#!/usr/bin/env python3
"""
Run Accuracy Benchmark - Comprehensive extraction accuracy evaluation.

Uses the new ExtractionEvaluator to provide detailed multi-tier metrics
and field-level analysis across multiple models.

This script loads extraction results from previous benchmark runs 
and evaluates them using the comprehensive accuracy framework.
"""
import sys
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root
sys.path.insert(0, str(Path.cwd()))

from tests.extraction_evaluator import ExtractionEvaluator, ModelEvaluation, generate_report
from tests.gold_standard_validation import ALL_GOLD_STANDARDS


def load_extractions_from_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Load extraction results from a CSV file."""
    if not csv_path.exists():
        return []
    
    extractions = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            extractions.append(dict(row))
    
    return extractions


def find_benchmark_results(output_base: Path) -> Dict[str, Dict]:
    """Find existing benchmark result CSVs."""
    results = {}
    
    # Look for model-specific output CSVs (actual file names from benchmark runs)
    model_files = [
        ("llama3.1:8b", output_base / "benchmark_run" / "results_llama3.1_8b.csv"),
        ("mistral:latest", output_base / "benchmark_run" / "results_mistral_latest.csv"),
        ("qwen2.5-coder:7b-instruct-q8_0", output_base / "benchmark_run" / "results_qwen2.5-coder_7b-instruct-q8_0.csv"),
        ("anthropic/claude-3.5-sonnet", output_base / "sonnet_benchmark" / "results_anthropic" / "claude-3.5-sonnet.csv"),
    ]
    
    for model_name, csv_file in model_files:
        if csv_file.exists():
            results[model_name] = {
                "csv_path": csv_file,
                "extractions": load_extractions_from_csv(csv_file),
            }
    
    return results


def main():
    print("="*70)
    print("SR-Architect: Comprehensive Extraction Accuracy Benchmark")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    base_dir = Path.cwd()
    output_base = base_dir / "tests" / "output"
    output_dir = output_base / "accuracy_benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load previous benchmark results
    print("\nLoading previous benchmark results...")
    benchmark_results = find_benchmark_results(output_base)
    
    if not benchmark_results:
        print("❌ No benchmark results found. Run benchmarks first:")
        print("   python3 tests/run_model_comparison.py --all")
        print("   python3 tests/run_sonnet_benchmark.py")
        sys.exit(1)
    
    print(f"Found results for {len(benchmark_results)} models:")
    for model_name, data in benchmark_results.items():
        print(f"  - {model_name}: {len(data['extractions'])} extractions")
    
    # Initialize evaluator
    evaluator = ExtractionEvaluator()
    
    # Evaluate each model
    all_evaluations: List[ModelEvaluation] = []
    
    # Processing times from previous runs (hardcoded from benchmark output)
    processing_times = {
        "llama3.1:8b": 389.16,
        "mistral:latest": 585.17,
        "qwen2.5-coder:7b-instruct-q8_0": 415.49,
        "anthropic/claude-3.5-sonnet": 99.71,
    }
    
    for model_name, data in benchmark_results.items():
        print(f"\nEvaluating: {model_name}")
        
        model_eval = evaluator.evaluate_model(
            model_name=model_name,
            gold_standards=ALL_GOLD_STANDARDS,
            extractions=data["extractions"],
            processing_time=processing_times.get(model_name, 0),
        )
        
        all_evaluations.append(model_eval)
        
        # Print quick stats
        print(f"  Exact: {model_eval.avg_exact_match:.0%}, "
              f"Terms: {model_eval.avg_key_term_match:.0%}, "
              f"Semantic: {model_eval.avg_semantic_match:.0%}, "
              f"CAS: {model_eval.avg_clinical_accuracy:.2f}")
    
    # Generate report
    report_path = output_dir / "accuracy_report.md"
    report = generate_report(all_evaluations, report_path)
    
    # Save raw metrics as JSON
    metrics_path = output_dir / "accuracy_metrics.json"
    metrics = {
        "generated": datetime.now().isoformat(),
        "gold_standards_used": len(ALL_GOLD_STANDARDS),
        "models": {}
    }
    
    for eval in all_evaluations:
        metrics["models"][eval.model_name] = {
            "processing_time_s": eval.processing_time,
            "documents_evaluated": len(eval.document_evaluations),
            "exact_match_rate": eval.avg_exact_match,
            "key_term_rate": eval.avg_key_term_match,
            "semantic_match_rate": eval.avg_semantic_match,
            "completeness_rate": eval.avg_completeness,
            "clinical_accuracy_score": eval.avg_clinical_accuracy,
            "field_stats": {k: {kk: vv for kk, vv in v.items() if kk != "errors"} 
                           for k, v in eval.get_field_stats().items()},
        }
    
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    
    # Print summary table
    print("\n" + "="*70)
    print("COMPREHENSIVE ACCURACY RESULTS")
    print("="*70)
    print("\n| Model | Time | Exact | Key Terms | Semantic | Complete | CAS |")
    print("|-------|------|-------|-----------|----------|----------|-----|")
    
    for eval in sorted(all_evaluations, key=lambda e: -e.avg_clinical_accuracy):
        cost = "$" if "claude" in eval.model_name.lower() else "FREE"
        print(
            f"| {eval.model_name} | {eval.processing_time:.0f}s | "
            f"{eval.avg_exact_match:.0%} | {eval.avg_key_term_match:.0%} | "
            f"{eval.avg_semantic_match:.0%} | {eval.avg_completeness:.0%} | "
            f"**{eval.avg_clinical_accuracy:.2f}** |"
        )
    
    # Field breakdown for best model
    best_model = max(all_evaluations, key=lambda e: e.avg_clinical_accuracy)
    print(f"\n--- Field Breakdown: {best_model.model_name} ---")
    print("| Field | Exact | Terms | Semantic | Errors |")
    print("|-------|-------|-------|----------|--------|")
    
    field_stats = best_model.get_field_stats()
    for field_name, stats in field_stats.items():
        total = stats["total"]
        errors = stats.get("errors", {})
        error_counts = [f"{v}{k[0]}" for k, v in errors.items() if v > 0]
        error_str = ",".join(error_counts) if error_counts else "-"
        
        print(f"| {field_name:20} | {stats['exact']}/{total} | "
              f"{stats['terms']}/{total} | {stats['semantic']}/{total} | {error_str} |")
    
    # Error examples
    print(f"\n--- Sample Errors ---")
    for i, ex in enumerate(best_model.get_error_examples(3), 1):
        print(f"{i}. [{ex['error_type']}] {ex['field']}")
        print(f"   Gold: {ex['gold'][:60]}...")
        print(f"   Got:  {ex['extracted'][:60]}...")
        print()
    
    print(f"\n✓ Detailed report: {report_path}")
    print(f"✓ Metrics JSON: {metrics_path}")
    print("\n✓ Evaluation complete!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Run Sonnet Benchmark (Claude 3.5 Sonnet via OpenRouter)
Compares against local LLM baseline results.
"""
import sys
import os
from pathlib import Path
from typing import List, Dict

# Add project root
sys.path.append(str(Path.cwd()))

from core.benchmark import ModelBenchmark
from tests.gold_standard_validation import ALL_GOLD_STANDARDS, validate_extraction

def gold_standard_validator(results: List[Dict]) -> float:
    """
    Adapter function: 
    Takes list of extraction results (dicts), runs validation against gold standards,
    returns average semantic match score (0.0 - 1.0).
    """
    total_semantic_matches = 0
    total_fields_checked = 0
    
    print(f"\nRunning validation on {len(results)} extracted records...")
    
    for extracted_row in results:
        # Find matching gold standard
        matched_gold = None
        for gold in ALL_GOLD_STANDARDS:
            if gold["source"] in str(extracted_row.values()):
                matched_gold = gold
                break
        
        if not matched_gold:
            continue
            
        validation_results = validate_extraction(matched_gold, extracted_row)
        
        for res in validation_results:
            total_fields_checked += 1
            if res.semantic_match:
                total_semantic_matches += 1
                
    if total_fields_checked == 0:
        return 0.0
        
    score = total_semantic_matches / total_fields_checked
    print(f"Validation Score: {score:.2f} ({total_semantic_matches}/{total_fields_checked} fields)")
    return score

def main():
    print("=" * 60)
    print("SR-Architect: Claude Sonnet Benchmark")
    print("=" * 60)
    
    # Configuration
    base_dir = Path.cwd()
    papers_dir = base_dir / "papers_benchmark"
    output_dir = base_dir / "tests" / "output" / "sonnet_benchmark"
    
    # Claude 3.5 Sonnet via OpenRouter
    models = ["anthropic/claude-3.5-sonnet"]
    
    benchmark = ModelBenchmark(
        papers_dir=str(papers_dir),
        output_dir=str(output_dir)
    )
    
    # Run with OpenRouter provider
    results = benchmark.run_benchmark(
        models=models,
        sample_size=3,
        provider="openrouter",  # Use OpenRouter for Claude
        validator_callback=gold_standard_validator
    )
    
    # Compare with local LLM results
    print("\n" + "=" * 60)
    print("COMPARISON: Local LLMs vs Claude Sonnet")
    print("=" * 60)
    
    # Local LLM baseline (from previous benchmark)
    local_results = [
        {"model": "llama3.1:8b", "time": 389.16, "success": "2/3", "val_score": 0.27},
        {"model": "mistral:latest", "time": 585.17, "success": "3/3", "val_score": 0.21},
        {"model": "qwen2.5-coder:7b-instruct-q8_0", "time": 415.49, "success": "3/3", "val_score": 0.18},
    ]
    
    print("\n| Model | Time (s) | Success | Val Score | Cost Tier |")
    print("|-------|----------|---------|-----------|-----------|")
    
    for r in local_results:
        print(f"| {r['model']} | {r['time']:.1f} | {r['success']} | {r['val_score']:.2f} | FREE |")
    
    for r in results:
        cost = "$" if "claude" in r.model_name.lower() or "gpt" in r.model_name.lower() else "FREE"
        print(f"| {r.model_name} | {r.total_time:.1f} | {r.success_count}/{r.docs_processed} | {r.validation_score_avg:.2f} | {cost} |")
    
    print("\n✓ Benchmark complete!")
    
    # Exit with error if Sonnet had 100% failure
    if any(r.success_count == 0 for r in results):
        sys.exit(1)

if __name__ == "__main__":
    main()

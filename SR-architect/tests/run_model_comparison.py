#!/usr/bin/env python3
"""
Run Model Comparison (Llama/Mistral/Qwen)
Includes integration with Gold Standard Validation.
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
            # Simple heuristic: check if source filename is contained in row string representation
            # Ideally we check a specific filename field
            if gold["source"] in str(extracted_row.values()):
                matched_gold = gold
                break
        
        if not matched_gold:
            continue
            
        validation_results = validate_extraction(matched_gold, extracted_row)
        
        # Count semantic matches
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
    print("--- SR-Architect Model Comparison ---")
    
    # Configuration
    base_dir = Path.cwd()
    papers_dir = base_dir / "papers_benchmark"
    output_dir = base_dir / "tests" / "output" / "benchmark_run"
    
    # Models to test (Available in local Ollama - from 'ollama list')
    models = ["llama3.1:8b", "mistral:latest"] 
    
    # Check if we should include qwen or others via args
    if "--all" in sys.argv:
        models.append("qwen2.5-coder:7b-instruct-q8_0")
    
    # Use 3 samples for broader benchmark (or pass --quick for 2)
    sample_size = 2 if "--quick" in sys.argv else 3
    
    benchmark = ModelBenchmark(
        papers_dir=str(papers_dir),
        output_dir=str(output_dir)
    )
    
    # Run
    results = benchmark.run_benchmark(
        models=models,
        sample_size=sample_size,
        validator_callback=gold_standard_validator
    )
    
    # Exit with error if any model had 100% failure
    if any(r.success_count == 0 for r in results):
        sys.exit(1)

if __name__ == "__main__":
    main()

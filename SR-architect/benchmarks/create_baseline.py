
import os
import json
import asyncio
from pathlib import Path
from core.service import ExtractionService
from core.schema_builder import get_case_report_schema
from core.config import settings

from core.token_tracker import TokenTracker

def create_baseline():
    papers_dir = Path("papers_benchmark")
    output_dir = Path("benchmarks/golden_dataset")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize tracker with log file
    tracker = TokenTracker(log_file=output_dir / "logs/token_usage.jsonl")
    
    # Use current settings (defaults to OpenRouter/Sonnet if configured, or user default)
    # We want the "Best" model for the golden set.
    # Assuming the env is set up for the "Current Baseline".
    
    service = ExtractionService(verbose=True, token_tracker=tracker)
    
    # Use Case Report schema
    fields = get_case_report_schema()
    
    print(f"Running baseline extraction on {len(list(papers_dir.glob('*.pdf')))} papers...")
    
    # We want detailed results, so we might need to access the pipeline directly or 
    # use run_extraction and rely on it saving something, or modify run_extraction to return data.
    # run_extraction returns a summary dict.
    # However, the callback receives the data!
    
    results = {}
    
    def result_callback(filename, data, status):
        if status == "success":
            # data is the extracted dict
            results[filename] = data
            
            # Save individual golden file
            with open(output_dir / f"{filename}.json", "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved golden: {filename}")
        else:
            print(f"Failed: {filename} - {data}")

    summary = service.run_extraction(
        papers_dir=str(papers_dir),
        fields=fields,
        output_csv=str(output_dir / "baseline.csv"),
        callback=result_callback,
        workers=3, # Parallel execution
        vectorize=False, # Disable vectorization for speed/stability of baseline
        resume=True # Resume from checkpoint to avoid reprocessing
    )
    
    # Save metrics
    metrics = {
        "cost_usd": summary["cost_usd"],
        "tokens": summary["tokens"],
        "total_files": summary["total_files"],
        "successful": len(results)
    }
    
    with open(output_dir / "baseline_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print("Baseline creation complete.")

if __name__ == "__main__":
    create_baseline()

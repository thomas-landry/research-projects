
import json
from pathlib import Path

def calculate_metrics():
    # Parse token_usage.jsonl from the output directory
    # Note: create_baseline.py output to benchmarks/golden_dataset/baseline.csv
    # So logs are in benchmarks/golden_dataset/logs/token_usage.jsonl?
    # No, ExtractionService sets log_dir based on output_path parent.
    # output_path = benchmarks/golden_dataset/baseline.csv
    # log_dir = benchmarks/golden_dataset/logs
    
    log_dir = Path("benchmarks/golden_dataset/logs")
    usage_file = log_dir.parent / "token_usage.jsonl" # TokenTracker usually saves to parent of log_dir? 
    # cli.py: tracker = TokenTracker(log_file=output_path.parent / "token_usage.jsonl")
    
    if not usage_file.exists():
        print(f"Usage file not found: {usage_file}")
        # Try looking in default location if service didn't override correctly?
        # ExtractionService uses self.tracker.
        # If passed from outside, it uses that.
        # In create_baseline.py: service = ExtractionService(verbose=True).
        # service.__init__ initializes TokenTracker(). Default log_file is "token_usage.jsonl" in cwd?
        # No, TokenTracker default is None? 
        # Check core/token_tracker.py
        return

    print(f"Reading metrics from {usage_file}")
    
    total_tokens = 0
    total_cost = 0.0
    papers = set()
    
    with open(usage_file, "r") as f:
        for line in f:
            try:
                record = json.loads(line)
                total_tokens += record.get("total_tokens", 0)
                total_cost += record.get("cost_usd", 0.0)
                if "filename" in record:
                    papers.add(record["filename"])
            except:
                pass
                
    print(f"Total Papers: {len(papers)}")
    print(f"Total Tokens: {total_tokens}")
    print(f"Total Cost: ${total_cost:.4f}")
    
    # Save to baseline_metrics_full.json
    metrics = {
        "total_files": len(papers),
        "tokens": total_tokens,
        "cost_usd": total_cost,
        "avg_cost_per_paper": total_cost / len(papers) if papers else 0
    }
    
    with open("benchmarks/golden_dataset/baseline_metrics_full.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    calculate_metrics()

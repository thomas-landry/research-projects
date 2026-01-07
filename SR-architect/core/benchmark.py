"""
Model Benchmark Harness
Compares performance of different local LLMs for the SR extraction task.
"""
import time
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from rich.console import Console
from rich.table import Table

from core.service import ExtractionService
from core.parser import DocumentParser
from core.schema_builder import get_case_report_schema, build_extraction_model
from core.token_tracker import TokenTracker

@dataclass
class BenchmarkResult:
    """Result for a single model run."""
    model_name: str
    total_time: float
    docs_processed: int
    success_count: int
    tokens_per_second: float = 0.0
    validation_score_avg: float = 0.0
    error_rate: float = 0.0
    errors: List[str] = field(default_factory=list)

class ModelBenchmark:
    """Harness to run extraction benchmarks across multiple models."""
    
    def __init__(self, papers_dir: str, output_dir: str):
        self.papers_dir = Path(papers_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.console = Console()
        
    def run_benchmark(
        self, 
        models: List[str], 
        sample_size: int = 3,
        provider: str = "ollama",
        validator_callback: Optional[Any] = None
    ) -> List[BenchmarkResult]:
        """
        Run benchmark for list of models.
        
        Args:
            models: List of model names
            sample_size: Number of papers to process
            provider: LLM provider
            validator_callback: Function accepting (results_list) -> float (score)
        """
        results = []
        
        # Setup schema (fixed for consistency)
        schema_fields = get_case_report_schema()
        
        for model in models:
            self.console.print(f"\n[bold cyan]Benchmarking Model: {model}[/bold cyan]")
            
            # Setup tracker for this run
            tracker = TokenTracker(log_file=self.output_dir / f"token_usage_{model.replace(':', '_')}.jsonl")
            
            # Initialize Service
            service = ExtractionService(
                provider=provider,
                model=model,
                token_tracker=tracker,
                verbose=False
            )
            
            start_time = time.time()
            
            # Run Extraction
            summary = service.run_extraction(
                papers_dir=str(self.papers_dir),
                fields=schema_fields,
                output_csv=str(self.output_dir / f"results_{model.replace(':', '_')}.csv"),
                hierarchical=True, # Use full pipeline for rigorous test
                theme="pulmonary meningothelial nodules", # Hardcoded valid theme for verification set
                max_iter=1, # Limit iterations for speed
                resume=False,
                limit=sample_size
            )
            
            duration = time.time() - start_time
            
            # Calculate Metrics
            total_docs = summary["total_files"]
            success = summary["parsed_files"] - len(summary["failed_files"])
            
            # Run Validation if callback provided
            validation_score = 0.0
            if validator_callback and success > 0:
                try:
                    # We need the actual results list. 
                    # If run_extraction returned just summary, we might need to load from CSV or StateManager
                    # For now, let's assume we can load the CSV we just wrote
                    import pandas as pd
                    csv_path = self.output_dir / f"results_{model.replace(':', '_')}.csv"
                    if csv_path.exists():
                        df = pd.read_csv(csv_path)
                        # Callback expects list of dicts
                        validation_score = validator_callback(df.to_dict(orient="records"))
                except Exception as e:
                    self.console.print(f"[red]Validation failed: {e}[/red]")
            
            res = BenchmarkResult(
                model_name=model,
                total_time=duration,
                docs_processed=total_docs,
                success_count=success,
                error_rate=len(summary["failed_files"]) / total_docs if total_docs > 0 else 0,
                validation_score_avg=validation_score,
                errors=[e[1] for e in summary["failed_files"]]
            )
            results.append(res)
            
            self.console.print(f"[green]✓ Completed in {duration:.2f}s (Success: {success}/{total_docs}, Acc: {validation_score:.2f})[/green]")
            
        self._save_report(results)
        return results

    def _save_report(self, results: List[BenchmarkResult]):
        """Save comparison report."""
        report_path = self.output_dir / "benchmark_report.md"
        
        with open(report_path, "w") as f:
            f.write("# Model Benchmark Report\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("| Model | Time (s) | Success Rate | Val Score | Errors |\n")
            f.write("|-------|----------|--------------|-----------|--------|\n")
            
            for r in results:
                success_rate = f"{r.success_count}/{r.docs_processed}"
                f.write(f"| {r.model_name} | {r.total_time:.2f} | {success_rate} | {r.validation_score_avg:.2f} | {len(r.errors)} |\n")
                
        self.console.print(f"\n[bold]Report saved to {report_path}[/bold]")


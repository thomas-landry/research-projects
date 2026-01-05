#!/usr/bin/env python3
"""
Audit Logger for full extraction provenance tracking.

Creates JSONL logs for reproducibility and methods/supplementary documentation.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ExtractionLogEntry:
    """A single extraction log entry."""
    timestamp: str
    filename: str
    status: str  # "success", "error", "skipped"
    chunks_created: int
    vectors_stored: int
    extraction_model: str
    fields_extracted: Dict[str, Any]
    token_usage: Optional[Dict[str, int]] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """
    Structured audit logging for extraction pipeline.
    
    Creates JSONL logs that can be used for:
    - Reproducibility documentation in methods section
    - Supplementary materials
    - Debugging and error analysis
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        session_name: Optional[str] = None,
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory to store logs
            session_name: Optional session identifier
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session-specific log file
        if session_name:
            self.session_name = session_name
        else:
            self.session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.log_file = self.log_dir / f"extraction_{self.session_name}.jsonl"
        self.summary_file = self.log_dir / f"summary_{self.session_name}.json"
        
        # Session stats
        self.entries: List[ExtractionLogEntry] = []
        self.start_time = datetime.now()
    
    def log_extraction(
        self,
        filename: str,
        status: str,
        chunks_created: int = 0,
        vectors_stored: int = 0,
        extraction_model: str = "",
        fields_extracted: Optional[Dict[str, Any]] = None,
        token_usage: Optional[Dict[str, int]] = None,
        duration_seconds: float = 0.0,
        error_message: Optional[str] = None,
    ):
        """
        Log a single extraction event.
        
        Args:
            filename: Source PDF filename
            status: Extraction status
            chunks_created: Number of chunks from parsing
            vectors_stored: Number of vectors stored
            extraction_model: LLM model used
            fields_extracted: Extracted field values
            token_usage: Token usage stats
            duration_seconds: Processing time
            error_message: Error message if failed
        """
        entry = ExtractionLogEntry(
            timestamp=datetime.now().isoformat(),
            filename=filename,
            status=status,
            chunks_created=chunks_created,
            vectors_stored=vectors_stored,
            extraction_model=extraction_model,
            fields_extracted=fields_extracted or {},
            token_usage=token_usage,
            duration_seconds=duration_seconds,
            error_message=error_message,
        )
        
        self.entries.append(entry)
        
        # Append to JSONL file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
    
    def log_success(
        self,
        filename: str,
        chunks: int,
        vectors: int,
        model: str,
        extracted: Dict[str, Any],
        duration: float,
    ):
        """Convenience method for successful extraction."""
        self.log_extraction(
            filename=filename,
            status="success",
            chunks_created=chunks,
            vectors_stored=vectors,
            extraction_model=model,
            fields_extracted=extracted,
            duration_seconds=duration,
        )
    
    def log_error(self, filename: str, error: str, duration: float = 0.0):
        """Convenience method for failed extraction."""
        self.log_extraction(
            filename=filename,
            status="error",
            error_message=error,
            duration_seconds=duration,
        )
    
    def log_skipped(self, filename: str, reason: str):
        """Convenience method for skipped files."""
        self.log_extraction(
            filename=filename,
            status="skipped",
            error_message=reason,
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate session summary statistics."""
        total = len(self.entries)
        successful = sum(1 for e in self.entries if e.status == "success")
        failed = sum(1 for e in self.entries if e.status == "error")
        skipped = sum(1 for e in self.entries if e.status == "skipped")
        
        total_chunks = sum(e.chunks_created for e in self.entries)
        total_vectors = sum(e.vectors_stored for e in self.entries)
        total_duration = sum(e.duration_seconds for e in self.entries)
        
        return {
            "session_name": self.session_name,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "success_rate": f"{successful/total*100:.1f}%" if total > 0 else "N/A",
            "total_chunks": total_chunks,
            "total_vectors": total_vectors,
            "total_duration_seconds": round(total_duration, 2),
            "avg_duration_per_file": round(total_duration / total, 2) if total > 0 else 0,
            "log_file": str(self.log_file),
        }
    
    def save_summary(self):
        """Save summary to JSON file."""
        summary = self.get_summary()
        with open(self.summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        return summary
    
    def generate_methods_text(self) -> str:
        """
        Generate reproducibility text for methods section.
        
        Returns:
            Markdown text suitable for methods/supplementary
        """
        summary = self.get_summary()
        
        # Get unique models used
        models = set(e.extraction_model for e in self.entries if e.extraction_model)
        
        text = f"""## Data Extraction Methods

### Automated Extraction Pipeline

Data extraction was performed using SR-Architect, an automated systematic review 
extraction pipeline. The pipeline processed {summary['total_files']} full-text PDFs 
with the following specifications:

- **Extraction Model**: {', '.join(models) if models else 'N/A'}
- **Processing Time**: {summary['total_duration_seconds']:.1f} seconds total
- **Success Rate**: {summary['success_rate']}
- **Documents Successfully Extracted**: {summary['successful']}/{summary['total_files']}

### Quality Assurance

Each extraction included source quotations for traceability. Failed extractions 
({summary['failed']} files) were flagged for manual review. Complete extraction 
logs are available in the supplementary materials (File: {self.log_file.name}).

### Reproducibility

The extraction session ID is `{summary['session_name']}`. Full provenance logs 
are provided in JSONL format for independent verification.
"""
        return text
    
    def print_summary(self):
        """Print summary to console."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        summary = self.get_summary()
        
        table = Table(title="Extraction Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Files", str(summary["total_files"]))
        table.add_row("Successful", str(summary["successful"]))
        table.add_row("Failed", str(summary["failed"]))
        table.add_row("Skipped", str(summary["skipped"]))
        table.add_row("Success Rate", summary["success_rate"])
        table.add_row("Total Chunks", str(summary["total_chunks"]))
        table.add_row("Total Vectors", str(summary["total_vectors"]))
        table.add_row("Total Duration", f"{summary['total_duration_seconds']:.1f}s")
        
        console.print(table)
        console.print(f"\n[dim]Log file: {self.log_file}[/dim]")


if __name__ == "__main__":
    # Demo
    logger = AuditLogger(log_dir="./logs", session_name="demo")
    
    # Simulate some extractions
    logger.log_success(
        filename="paper1.pdf",
        chunks=15,
        vectors=15,
        model="claude-sonnet-4-20250514",
        extracted={"patient_age": "52", "patient_sex": "Female"},
        duration=2.5,
    )
    
    logger.log_error("paper2.pdf", "PDF parsing failed", duration=0.5)
    
    logger.log_success(
        filename="paper3.pdf",
        chunks=22,
        vectors=22,
        model="claude-sonnet-4-20250514",
        extracted={"patient_age": "67", "patient_sex": "Male"},
        duration=3.1,
    )
    
    logger.print_summary()
    logger.save_summary()
    
    print("\n--- Methods Text ---")
    print(logger.generate_methods_text())

#!/usr/bin/env python3
"""
Pipeline State Manager for checkpointing and resume capability.

Enables extraction to resume from where it left off after crashes or interruptions.
"""

import json

from pathlib import Path
from typing import Set, Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PipelineState:
    """
    Persistent state for the extraction pipeline.
    
    Tracks:
    - Which papers have been processed
    - Which papers failed (and why)
    - Extracted data so far
    - Configuration used
    """
    
    # Session metadata
    session_id: str = ""
    started_at: str = ""
    schema_name: str = ""
    papers_dir: str = ""
    
    # Progress tracking
    completed_papers: Set[str] = field(default_factory=set)
    failed_papers: Dict[str, str] = field(default_factory=dict)  # filename -> error
    skipped_papers: Set[str] = field(default_factory=set)
    
    # Extracted data (kept in memory, saved to CSV separately)
    extracted_count: int = 0
    
    # For resume
    last_processed: str = ""
    
    def __post_init__(self):
        if not self.session_id:
            # Use ISO format without colons for filesystem-safe session ID
            self.session_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
    
    def should_process(self, paper_name: str) -> bool:
        """Check if a paper should be processed (not already done or failed)."""
        return (
            paper_name not in self.completed_papers and
            paper_name not in self.failed_papers and
            paper_name not in self.skipped_papers
        )
    
    def mark_completed(self, paper_name: str):
        """Mark a paper as successfully extracted."""
        self.completed_papers.add(paper_name)
        self.last_processed = paper_name
        self.extracted_count += 1
    
    def mark_failed(self, paper_name: str, error: str):
        """Mark a paper as failed with error message."""
        self.failed_papers[paper_name] = error
        self.last_processed = paper_name
    
    def mark_skipped(self, paper_name: str):
        """Mark a paper as skipped (e.g., insufficient text)."""
        self.skipped_papers.add(paper_name)
        self.last_processed = paper_name
    
    def get_progress(self) -> dict:
        """Get progress summary."""
        total = len(self.completed_papers) + len(self.failed_papers) + len(self.skipped_papers)
        return {
            "completed": len(self.completed_papers),
            "failed": len(self.failed_papers),
            "skipped": len(self.skipped_papers),
            "total_processed": total,
            "last_processed": self.last_processed,
        }
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "schema_name": self.schema_name,
            "papers_dir": self.papers_dir,
            "completed_papers": list(self.completed_papers),
            "failed_papers": self.failed_papers,
            "skipped_papers": list(self.skipped_papers),
            "extracted_count": self.extracted_count,
            "last_processed": self.last_processed,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PipelineState":
        """Create from dict (for JSON loading)."""
        return cls(
            session_id=data.get("session_id", ""),
            started_at=data.get("started_at", ""),
            schema_name=data.get("schema_name", ""),
            papers_dir=data.get("papers_dir", ""),
            completed_papers=set(data.get("completed_papers", [])),
            failed_papers=data.get("failed_papers", {}),
            skipped_papers=set(data.get("skipped_papers", [])),
            extracted_count=data.get("extracted_count", 0),
            last_processed=data.get("last_processed", ""),
        )


class StateManager:
    """
    Manages pipeline state persistence.
    
    Usage:
        manager = StateManager("./output/pipeline_state.json")
        state = manager.load_or_create()
        
        for paper in papers:
            if state.should_process(paper):
                try:
                    extract(paper)
                    state.mark_completed(paper)
                except Exception as e:
                    state.mark_failed(paper, str(e))
                manager.save(state)  # Save after each paper
    """
    
    def __init__(self, state_file: str = "./output/pipeline_state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def exists(self) -> bool:
        """Check if a saved state exists."""
        return self.state_file.exists()
    
    def load(self) -> Optional[PipelineState]:
        """Load existing state from file."""
        if not self.exists():
            return None
        
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            return PipelineState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load state file: {e}")
            return None
    
    def load_or_create(
        self,
        schema_name: str = "",
        papers_dir: str = "",
    ) -> PipelineState:
        """Load existing state or create new one."""
        existing = self.load()
        
        if existing:
            print(f"📂 Resuming session: {existing.session_id}")
            print(f"   Progress: {existing.get_progress()}")
            return existing
        
        return PipelineState(
            schema_name=schema_name,
            papers_dir=papers_dir,
        )
    
    def save(self, state: PipelineState):
        """Save state to file."""
        with open(self.state_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
    
    def clear(self):
        """Delete saved state (start fresh)."""
        if self.exists():
            self.state_file.unlink()


if __name__ == "__main__":
    # Demo
    manager = StateManager("./test_state.json")
    
    # Create new state
    state = manager.load_or_create(schema_name="case_report", papers_dir="./papers")
    
    # Simulate processing
    state.mark_completed("paper1.pdf")
    state.mark_completed("paper2.pdf")
    state.mark_failed("paper3.pdf", "PDF parsing error")
    state.mark_skipped("paper4.pdf")
    
    # Save
    manager.save(state)
    print(f"Saved state: {state.get_progress()}")
    
    # Load back
    loaded = manager.load()
    print(f"Loaded state: {loaded.get_progress()}")
    
    # Check should_process
    print(f"Should process paper1? {loaded.should_process('paper1.pdf')}")  # False
    print(f"Should process paper5? {loaded.should_process('paper5.pdf')}")  # True
    
    # Cleanup
    manager.clear()

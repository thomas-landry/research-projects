"""
Centralized data types for SR-Architect.
Avoids circular imports and standardizes data structures.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel

@dataclass
class EvidenceFrame:
    """
    Precise provenance for an extracted piece of information.
    Based on llm-ie FrameExtractionUnit.
    """
    text: str
    doc_id: str
    start_char: int
    end_char: int
    section: str = "Unknown"
    content: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "start": self.start_char,
            "end": self.end_char,
            "section": self.section,
            "content": self.content
        }

@dataclass
class ExtractionLog:
    """Log entry for extraction events."""
    timestamp: str
    message: str
    level: str = "INFO"

@dataclass
class ExtractionWarning:
    """Warning encountered during extraction."""
    message: str
    context: Optional[str] = None

@dataclass
class IterationRecord:
    """Record of a single extraction iteration."""
    iteration_number: int
    accuracy_score: float
    consistency_score: float
    overall_score: float
    issues_count: int
    suggestions: List[str]

@dataclass
class PipelineResult:
    """Complete result from the hierarchical extraction pipeline."""
    # Core outputs
    final_data: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    
    # Validation info
    final_accuracy_score: float
    final_consistency_score: float
    final_overall_score: float
    passed_validation: bool
    
    # Pipeline metadata
    iterations: int
    iteration_history: List[IterationRecord] = field(default_factory=list)
    
    # Token/filtering stats
    content_filter_stats: Dict[str, Any] = field(default_factory=dict)
    relevance_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Source info
    source_filename: str = ""
    extraction_timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "final_data": self.final_data,
            "evidence": self.evidence,
            "validation": {
                "accuracy_score": self.final_accuracy_score,
                "consistency_score": self.final_consistency_score,
                "overall_score": self.final_overall_score,
                "passed": self.passed_validation,
                "iterations": self.iterations,
            },
            "iteration_history": [
                {
                    "iteration": r.iteration_number,
                    "accuracy": r.accuracy_score,
                    "consistency": r.consistency_score,
                    "overall": r.overall_score,
                    "issues": r.issues_count,
                    "suggestions": r.suggestions
                } 
                for r in self.iteration_history
            ],
            "metadata": {
                "source": self.source_filename,
                "timestamp": self.extraction_timestamp,
                "filter_stats": self.content_filter_stats,
                "relevance": self.relevance_stats,
            },
            "warnings": self.warnings
        }

    def save_evidence_json(self, output_dir: str) -> str:
        """Save evidence to a JSON sidecar file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename to prevent path traversal
        if self.source_filename:
            safe_name = Path(self.source_filename).name
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
            basename = Path(safe_name).stem if safe_name else "extraction"
        else:
            basename = "extraction"
        
        evidence_file = output_path / f"{basename}_evidence.json"
        
        # Final safety check
        if not evidence_file.resolve().is_relative_to(output_path.resolve()):
            raise ValueError(f"Invalid filename would escape output directory: {self.source_filename}")
        
        evidence_data = {
            "source_file": self.source_filename,
            "extraction_timestamp": self.extraction_timestamp,
            "evidence": self.evidence,
            "validation": {
                "accuracy_score": self.final_accuracy_score,
                "consistency_score": self.final_consistency_score,
                "iterations": self.iterations,
                "issues_resolved": [
                    f"Iteration {r.iteration_number}: {r.issues_count} issues"
                    for r in self.iteration_history
                    if r.issues_count > 0
                ],
            }
        }
        
        import json
        with open(evidence_file, 'w') as f:
            json.dump(evidence_data, f, indent=2)
            
        return str(evidence_file)

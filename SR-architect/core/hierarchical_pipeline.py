#!/usr/bin/env python3
"""
Hierarchical Extraction Pipeline.

Orchestrates the full extraction workflow:
Filter → Classify → Extract → Check → Iterate

Combines all components for rigorous, validated data extraction.
"""

import json
from datetime import datetime
from typing import Type, TypeVar, Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel

from .parser import ParsedDocument, DocumentChunk
from .content_filter import ContentFilter, FilterResult
from .relevance_classifier import RelevanceClassifier, RelevanceResult
from .extractor import StructuredExtractor, ExtractionWithEvidence, EvidenceItem
from .extraction_checker import ExtractionChecker, CheckerResult

T = TypeVar('T', bound=BaseModel)


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
                }
                for r in self.iteration_history
            ],
            "stats": {
                "content_filter": self.content_filter_stats,
                "relevance": self.relevance_stats,
            },
            "warnings": self.warnings,
            "source_filename": self.source_filename,
            "extraction_timestamp": self.extraction_timestamp,
        }
    
    def save_evidence_json(self, output_dir: str) -> str:
        """Save evidence to a JSON sidecar file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # BUG-005 FIX: Sanitize filename to prevent path traversal
        if self.source_filename:
            # Extract only the filename, stripping any directory components
            safe_name = Path(self.source_filename).name
            # Remove any remaining dangerous characters (keep alphanumeric, dots, underscores, hyphens)
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
            basename = Path(safe_name).stem if safe_name else "extraction"
        else:
            basename = "extraction"
        
        evidence_file = output_path / f"{basename}_evidence.json"
        
        # Final safety check: ensure file is within output directory
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
        
        with open(evidence_file, 'w') as f:
            json.dump(evidence_data, f, indent=2)
        
        return str(evidence_file)


class HierarchicalExtractionPipeline:
    """Full pipeline: Filter → Classify → Extract → Check → Iterate."""
    
    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        score_threshold: float = 0.8,
        max_iterations: int = 3,
        verbose: bool = False,
        examples: Optional[str] = None,
    ):
        """
        Initialize the hierarchical pipeline.
        
        Args:
            provider: LLM provider
            model: Model name
            score_threshold: Minimum confidence score to accept extraction
            max_iterations: Max feedback loops
            verbose: Enable debug logging
            examples: Few-shot examples string
        """
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize components
        self.content_filter = ContentFilter()
        self.relevance_classifier = RelevanceClassifier(
            provider=provider,
            model=model,
        )
        self.extractor = StructuredExtractor(
            provider=provider,
            model=model,
            examples=examples,
        )
        self.checker = ExtractionChecker(
            provider=provider,
            model=model,
        )
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Pipeline] {message}")
    
    def _build_context(self, chunks: List[DocumentChunk], max_chars: int = 15000) -> str:
        """Build extraction context from relevant chunks."""
        context_parts = []
        total_chars = 0
        
        for chunk in chunks:
            section_label = f"[{chunk.section}] " if chunk.section else ""
            chunk_text = f"{section_label}{chunk.text}\n\n"
            
            if total_chars + len(chunk_text) > max_chars:
                break
            
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        context = "".join(context_parts)
        
        if not context.strip():
            raise ValueError("Cannot build extraction context: no valid chunks available")
        
        return context

    def extract_document(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str,
    ) -> PipelineResult:
        """Full extraction with validation loop."""
        timestamp = datetime.now().isoformat()
        warnings: List[str] = []
        
        self._log(f"Starting extraction for: {document.filename}")
        
        # === Stage 1: Content Filtering ===
        self._log("Stage 1: Filtering content (removing affiliations, references)...")
        filter_result = self.content_filter.filter_chunks(document.chunks)
        filtered_chunks = filter_result.filtered_chunks
        
        if not filtered_chunks:
            warnings.append("All chunks were filtered out - using original chunks")
            filtered_chunks = document.chunks
            
        # === Stage 2: Relevance Classification ===
        self._log("Stage 2: Classifying chunk relevance...")
        schema_fields = list(schema.model_fields.keys()) if hasattr(schema, 'model_fields') else []
        relevant_chunks, relevance_results = self.relevance_classifier.get_relevant_chunks(
            filtered_chunks, theme, schema_fields
        )
        relevance_stats = self.relevance_classifier.get_classification_summary(relevance_results)
        
        if not relevant_chunks:
            warnings.append("No chunks classified as relevant - using all filtered chunks")
            relevant_chunks = filtered_chunks
            
        # === Stage 3: Extraction with Feedback Loop ===
        context = self._build_context(relevant_chunks)
        revision_prompts: List[str] = []
        iteration_history: List[IterationRecord] = []
        
        best_result: Optional[ExtractionWithEvidence] = None
        best_check: Optional[CheckerResult] = None
        
        for iteration in range(self.max_iterations):
            self._log(f"  Iteration {iteration + 1}/{self.max_iterations}...")
            
            # Track previous revision prompts to detect stagnation
            previous_prompts = revision_prompts.copy() if revision_prompts else []
            
            # Extract with evidence
            try:
                extraction = self.extractor.extract_with_evidence(
                    context, 
                    schema, 
                    filename=document.filename,
                    revision_prompts=revision_prompts if revision_prompts else None,
                )
            except Exception as e:
                warnings.append(f"Extraction failed on iteration {iteration + 1}: {str(e)}")
                self._log(f"    ERROR: {str(e)}")
                continue
            
            # Check extraction quality
            evidence_dicts = [e.model_dump() for e in extraction.evidence]
            check_result = self.checker.check(
                relevant_chunks,
                extraction.data,
                evidence_dicts,
                theme,
                threshold=self.score_threshold,
            )
            
            # Record iteration
            iteration_history.append(IterationRecord(
                iteration_number=iteration + 1,
                accuracy_score=check_result.accuracy_score,
                consistency_score=check_result.consistency_score,
                overall_score=check_result.overall_score,
                issues_count=len(check_result.issues),
                suggestions=check_result.suggestions,
            ))
            
            self._log(f"    Accuracy: {check_result.accuracy_score:.2f}, Consistency: {check_result.consistency_score:.2f}")
            self._log(f"    Overall: {check_result.overall_score:.2f}, Issues: {len(check_result.issues)}")
            
            # Track best result
            if best_check is None or check_result.overall_score > best_check.overall_score:
                best_result = extraction
                best_check = check_result
            
            # Check if passed
            if check_result.passed:
                self._log(f"  ✓ Passed validation on iteration {iteration + 1}")
                break
            
            # Prepare revision prompts for next iteration
            if check_result.suggestions:
                revision_prompts = check_result.suggestions
                
                # BUG-009 FIX: Detect stagnation
                if set(revision_prompts) == set(previous_prompts):
                    warnings.append(f"Stagnation detected at iteration {iteration + 1}")
                    self._log("    ⚠ Stagnation detected - stopping early")
                    break
                
                self._log(f"    Applying {len(revision_prompts)} revision suggestions...")
            else:
                # No specific suggestions but still failed
                if iteration == 0:
                    revision_prompts = ["Please review all extracted values carefully and ensure quotes match exactly."]
                else:
                    # Generic prompt already tried, stop to avoid stagnation
                    warnings.append("No actionable suggestions available, stopping early")
                    break
        else:
            # Max iterations reached
            warnings.append(f"Reached max iterations ({self.max_iterations}) without passing validation")
            score = best_check.overall_score if best_check else 0.0
            self._log(f"  ⚠ Max iterations reached, using best result (score: {score:.2f})")
        
        # Use best result if available
        if best_result is None or best_check is None:
            raise RuntimeError("Extraction failed on all iterations")
        
        # Build final result
        evidence_dicts = [e.model_dump() for e in best_result.evidence]
        
        return PipelineResult(
            final_data=best_result.data,
            evidence=evidence_dicts,
            final_accuracy_score=best_check.accuracy_score,
            final_consistency_score=best_check.consistency_score,
            final_overall_score=best_check.overall_score,
            passed_validation=best_check.passed,
            iterations=len(iteration_history),
            iteration_history=iteration_history,
            content_filter_stats=filter_result.token_stats,
            relevance_stats=relevance_stats,
            warnings=warnings,
            source_filename=document.filename,
            extraction_timestamp=timestamp,
        )
    
    def extract_from_text(
        self,
        text: str,
        schema: Type[T],
        theme: str,
        filename: str = "document",
    ) -> PipelineResult:
        """
        Extract from raw text (simplified interface).
        
        Args:
            text: Raw document text
            schema: Extraction schema
            theme: Meta-analysis theme
            filename: Source filename for tracking
            
        Returns:
            PipelineResult
        """
        # Create a simple parsed document from text
        from .parser import ParsedDocument, DocumentChunk
        
        # Split into paragraph chunks
        paragraphs = text.split('\n\n')
        chunks = [
            DocumentChunk(text=p.strip(), source_file=filename)
            for p in paragraphs if p.strip()
        ]
        
        doc = ParsedDocument(
            filename=filename,
            chunks=chunks,
            full_text=text,
        )
        
        return self.extract_document(doc, schema, theme)


if __name__ == "__main__":
    # Demo usage
    print("Hierarchical Extraction Pipeline")
    print("=" * 50)
    print()
    print("Usage:")
    print("  from core.hierarchical_pipeline import HierarchicalExtractionPipeline")
    print("  from core.parser import DocumentParser")
    print("  from core.schema_builder import get_case_report_schema, build_extraction_model")
    print()
    print("  # Initialize")
    print("  pipeline = HierarchicalExtractionPipeline(")
    print("      score_threshold=0.9,")
    print("      max_iterations=3,")
    print("  )")
    print()
    print("  # Parse document")
    print("  parser = DocumentParser()")
    print("  doc = parser.parse_pdf('paper.pdf')")
    print()
    print("  # Extract with validation")
    print("  schema = get_case_report_schema()")
    print("  Model = build_extraction_model(schema, 'CaseModel')")
    print("  result = pipeline.extract_document(doc, Model, theme='your theme')")
    print()
    print("  # Check results")
    print("  print(f'Score: {result.final_overall_score}')")
    print("  print(f'Iterations: {result.iterations}')")
    print("  print(f'Data: {result.final_data}')")

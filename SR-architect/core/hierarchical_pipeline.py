#!/usr/bin/env python3
"""
Hierarchical Extraction Pipeline.

Orchestrates the full extraction workflow:
Filter → Classify → Extract → Check → Iterate

Combines all components for rigorous, validated data extraction.
Refactored to be stateless and component-driven.
"""

import json
from datetime import datetime
from core import utils
from typing import Type, TypeVar, Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel
from core.config import settings

from .parser import ParsedDocument, DocumentChunk
from .content_filter import ContentFilter, FilterResult
from .relevance_classifier import RelevanceClassifier, RelevanceResult
from .extractor import StructuredExtractor, ExtractionWithEvidence, EvidenceItem
from .extraction_checker import ExtractionChecker, CheckerResult

# Agents
from agents.schema_discovery import SchemaDiscoveryAgent, FieldDefinition
from agents.quality_auditor import QualityAuditorAgent, AuditReport
from agents.meta_analyst import MetaAnalystAgent, MetaAnalysisFeasibility
from agents.conflict_resolver import ConflictResolverAgent
from agents.section_locator import SectionLocatorAgent

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
        provider: str = settings.LLM_PROVIDER,
        model: Optional[str] = settings.LLM_MODEL,
        score_threshold: float = settings.SCORE_THRESHOLD,
        max_iterations: int = settings.MAX_ITERATIONS,
        verbose: bool = False,
        examples: Optional[str] = None,
        quality_auditor: Optional[QualityAuditorAgent] = None,
        schema_discoverer: Optional[SchemaDiscoveryAgent] = None,
        meta_analyst: Optional[MetaAnalystAgent] = None,
        token_tracker: Optional["TokenTracker"] = None,
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
            quality_auditor: Optional injected QualityAuditorAgent
            schema_discoverer: Optional injected SchemaDiscoveryAgent
            meta_analyst: Optional injected MetaAnalystAgent
        """
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize TokenTracker if not provided
        if token_tracker is None:
            from core.token_tracker import TokenTracker
            self.token_tracker = TokenTracker()
        else:
            self.token_tracker = token_tracker
            
        # Initialize components
        self.content_filter = ContentFilter()
        self.relevance_classifier = RelevanceClassifier(
            provider=provider,
            model=model,
            token_tracker=self.token_tracker,
        )
        self.extractor = StructuredExtractor(
            provider=provider,
            model=model,
            examples=examples,
            token_tracker=self.token_tracker,
        )
        self.checker = ExtractionChecker(
            provider=provider,
            model=model,
            token_tracker=self.token_tracker,
        )
        
        # Use injected agents or create defaults
        self.quality_auditor = quality_auditor or QualityAuditorAgent(
            provider=provider, 
            model=model if model != "anthropic/claude-3-haiku" else "anthropic/claude-3.5-sonnet",
            token_tracker=self.token_tracker
        )
        self.schema_discoverer = schema_discoverer or SchemaDiscoveryAgent(
            provider=provider, 
            model=model,
            token_tracker=self.token_tracker
        )
        self.meta_analyst = meta_analyst or MetaAnalystAgent(
            provider=provider, 
            model=model,
            token_tracker=self.token_tracker
        )
        
        self.logger = utils.get_logger("HierarchicalPipeline")
    
    def _build_context(self, chunks: List[DocumentChunk], max_chars: int = settings.MAX_CONTEXT_CHARS) -> str:
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
        
        self.logger.info(f"Starting extraction for: {document.filename}")
        
        # === Stage 1: Content Filtering ===
        self.logger.info("Stage 1: Filtering content (removing affiliations, references)...")
        filter_result = self.content_filter.filter_chunks(document.chunks)
        filtered_chunks = filter_result.filtered_chunks
        
        if not filtered_chunks:
            warnings.append("All chunks were filtered out - using original chunks")
            filtered_chunks = document.chunks
            
        # === Stage 2: Relevance Classification ===
        self.logger.info("Stage 2: Classifying chunk relevance...")
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
            self.logger.info(f"  Iteration {iteration + 1}/{self.max_iterations}...")
            
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
                self.logger.info(f"    ERROR: {str(e)}")
                
                # Register error for debugging
                from core.error_registry import ErrorRegistry
                ErrorRegistry().register(
                    e, 
                    location="HierarchicalExtractionPipeline.extract_document",
                    context={"filename": document.filename, "iteration": iteration + 1}
                )
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
            
            # === NEW: Quality Audit ===
            # Run the specialized auditor to verify quotes against values
            audit_report = self.quality_auditor.audit_extraction(extraction.data, evidence_dicts)
            
            # If critical errors found, downgrade score and add specific suggestions
            if not audit_report.passed:
                check_result.overall_score *= 0.8  # Penalty
                check_result.passed = False
                for audit in audit_report.audits:
                    if not audit.is_correct:
                        check_result.issues.append(f"Audit failed for {audit.field_name}: {audit.explanation}")
                        check_result.suggestions.append(f"For {audit.field_name}: {audit.explanation}")
            
            
            # Record iteration
            iteration_history.append(IterationRecord(
                iteration_number=iteration + 1,
                accuracy_score=check_result.accuracy_score,
                consistency_score=check_result.consistency_score,
                overall_score=check_result.overall_score,
                issues_count=len(check_result.issues),
                suggestions=check_result.suggestions,
            ))
            
            self.logger.info(f"    Accuracy: {check_result.accuracy_score:.2f}, Consistency: {check_result.consistency_score:.2f}")
            self.logger.info(f"    Overall: {check_result.overall_score:.2f}, Issues: {len(check_result.issues)}")
            
            # Track best result
            if best_check is None or check_result.overall_score > best_check.overall_score:
                best_result = extraction
                best_check = check_result
            
            # Check if passed
            if check_result.passed:
                self.logger.info(f"  ✓ Passed validation on iteration {iteration + 1}")
                break
            
            # Prepare revision prompts for next iteration
            if check_result.suggestions:
                revision_prompts = check_result.suggestions
                
                # BUG-009 FIX: Detect stagnation
                if set(revision_prompts) == set(previous_prompts):
                    warnings.append(f"Stagnation detected at iteration {iteration + 1}")
                    self.logger.info("    ⚠ Stagnation detected - stopping early")
                    break
                
                self.logger.info(f"    Applying {len(revision_prompts)} revision suggestions...")
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
            self.logger.info(f"  ⚠ Max iterations reached, using best result (score: {score:.2f})")
        
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

    async def extract_document_async(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str,
    ) -> PipelineResult:
        """Full extraction with validation loop (Async)."""
        timestamp = datetime.now().isoformat()
        warnings: List[str] = []
        
        self.logger.info(f"Starting async extraction for: {document.filename}")
        
        # === Stage 1: Content Filtering (Sync -> Thread Offload) ===
        self.logger.info("Stage 1: Filtering content...")
        import asyncio
        loop = asyncio.get_running_loop()
        filter_result = await loop.run_in_executor(
            None, 
            lambda: self.content_filter.filter_chunks(document.chunks)
        )
        filtered_chunks = filter_result.filtered_chunks
        
        if not filtered_chunks:
            warnings.append("All chunks were filtered out - using original chunks")
            filtered_chunks = document.chunks
            
        # === Stage 2: Relevance Classification (Async) ===
        self.logger.info("Stage 2: Classifying chunk relevance (async)...")
        schema_fields = list(schema.model_fields.keys()) if hasattr(schema, 'model_fields') else []
        relevant_chunks, relevance_results = await self.relevance_classifier.get_relevant_chunks_async(
            filtered_chunks, theme, schema_fields
        )
        relevance_stats = self.relevance_classifier.get_classification_summary(relevance_results)
        
        if not relevant_chunks:
            warnings.append("No chunks classified as relevant - using all filtered chunks")
            relevant_chunks = filtered_chunks
            
        # === Stage 3: Extraction with Feedback Loop (Async) ===
        context = self._build_context(relevant_chunks)
        revision_prompts: List[str] = []
        iteration_history: List[IterationRecord] = []
        
        best_result: Optional[ExtractionWithEvidence] = None
        best_check: Optional[CheckerResult] = None
        
        for iteration in range(self.max_iterations):
            self.logger.info(f"  Iteration {iteration + 1}/{self.max_iterations} (async)...")
            
            previous_prompts = revision_prompts.copy() if revision_prompts else []
            
            try:
                extraction = await self.extractor.extract_with_evidence_async(
                    context, 
                    schema, 
                    filename=document.filename,
                    revision_prompts=revision_prompts if revision_prompts else None,
                )
            except Exception as e:
                warnings.append(f"Async extraction failed on iteration {iteration + 1}: {str(e)}")
                self.logger.info(f"    ERROR: {str(e)}")
                
                # Register error for debugging
                from core.error_registry import ErrorRegistry
                ErrorRegistry().register(
                    e, 
                    location="HierarchicalExtractionPipeline.extract_document_async",
                    context={"filename": document.filename, "iteration": iteration + 1}
                )
                continue
            
            evidence_dicts = [e.model_dump() for e in extraction.evidence]
            
            # Run Checker and Auditor concurrently
            import asyncio
            check_task = self.checker.check_async(
                relevant_chunks,
                extraction.data,
                evidence_dicts,
                theme,
                threshold=self.score_threshold,
            )
            audit_task = self.quality_auditor.audit_extraction_async(extraction.data, evidence_dicts)
            
            check_result, audit_report = await asyncio.gather(check_task, audit_task)
            
            if not audit_report.passed:
                check_result.overall_score *= 0.8
                check_result.passed = False
                for audit in audit_report.audits:
                    if not audit.is_correct:
                        check_result.issues.append(f"Audit failed for {audit.field_name}: {audit.explanation}")
                        check_result.suggestions.append(f"For {audit.field_name}: {audit.explanation}")
            
            iteration_history.append(IterationRecord(
                iteration_number=iteration + 1,
                accuracy_score=check_result.accuracy_score,
                consistency_score=check_result.consistency_score,
                overall_score=check_result.overall_score,
                issues_count=len(check_result.issues),
                suggestions=check_result.suggestions,
            ))
            
            self.logger.info(f"    Accuracy: {check_result.accuracy_score:.2f}, Consistency: {check_result.consistency_score:.2f}")
            self.logger.info(f"    Overall: {check_result.overall_score:.2f}, Issues: {len(check_result.issues)}")
            
            if best_check is None or check_result.overall_score > best_check.overall_score:
                best_result = extraction
                best_check = check_result
            
            if check_result.passed:
                self.logger.info(f"  ✓ Passed validation on iteration {iteration + 1}")
                break
            
            if check_result.suggestions:
                revision_prompts = check_result.suggestions
                if set(revision_prompts) == set(previous_prompts):
                    warnings.append(f"Stagnation detected at iteration {iteration + 1}")
                    self.logger.info("    ⚠ Stagnation detected - stopping early")
                    break
                self.logger.info(f"    Applying {len(revision_prompts)} revision suggestions...")
            else:
                if iteration == 0:
                    revision_prompts = ["Please review all extracted values carefully and ensure quotes match exactly."]
                else:
                    warnings.append("No actionable suggestions available, stopping early")
                    break
        else:
            warnings.append(f"Reached max iterations ({self.max_iterations}) without passing validation")
            score = best_check.overall_score if best_check else 0.0
            self.logger.info(f"  ⚠ Max iterations reached, using best result (score: {score:.2f})")
        
        if best_result is None or best_check is None:
            raise RuntimeError("Async extraction failed on all iterations")
        
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

    async def extract_from_text_async(
        self,
        text: str,
        schema: Type[T],
        theme: str,
        filename: str = "document",
    ) -> PipelineResult:
        """Async version of extract_from_text."""
        from .parser import ParsedDocument, DocumentChunk
        
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
        
        return await self.extract_document_async(doc, schema, theme)


    def discover_schema(self, papers_dir: str, sample_size: int = 3) -> List[FieldDefinition]:
        """Run adaptive schema discovery."""
        return self.schema_discoverer.discover_schema(papers_dir, sample_size)
        
    def assess_meta_analysis(self, results: List[PipelineResult]) -> MetaAnalysisFeasibility:
        """Assess feasibility of meta-analysis on results."""
        data = [r.final_data for r in results]
        return self.meta_analyst.assess_feasibility(data)


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
    print(f"      score_threshold={settings.SCORE_THRESHOLD},")
    print(f"      max_iterations={settings.MAX_ITERATIONS},")
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


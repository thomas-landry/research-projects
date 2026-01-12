#!/usr/bin/env python3
"""
Hierarchical Extraction Pipeline.

Orchestrates the full extraction workflow:
Filter → Classify → Extract → Check → Iterate

Combines all components for rigorous, validated data extraction.
Refactored to be stateless and component-driven.
"""

import json
import hashlib
from datetime import datetime
from core import utils
from typing import Type, TypeVar, Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel
from core.config import settings

from .parser import ParsedDocument, DocumentChunk
from .content_filter import ContentFilter, FilterResult
from .relevance_classifier import RelevanceClassifier, RelevanceResult
from core.data_types import PipelineResult, IterationRecord, ExtractionLog, ExtractionWarning
from core.semantic_chunker import SemanticChunker
from .extractor import StructuredExtractor, ExtractionWithEvidence, EvidenceItem
from .extraction_checker import ExtractionChecker, CheckerResult
from .regex_extractor import RegexExtractor, RegexResult
from .abstract_first_extractor import AbstractFirstExtractor, AbstractExtractionResult
from .pubmed_fetcher import PubMedFetcher
from .two_pass_extractor import TwoPassExtractor, ModelCascader, ExtractionTier
from core.sentence_extractor import SentenceExtractor

# Agents
from agents.schema_discovery import SchemaDiscoveryAgent, FieldDefinition
from agents.quality_auditor import QualityAuditorAgent, AuditReport
from agents.meta_analyst import MetaAnalystAgent, MetaAnalysisFeasibility
from agents.conflict_resolver import ConflictResolverAgent
from agents.section_locator import SectionLocatorAgent

T = TypeVar('T', bound=BaseModel)





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
        
        # Initialize abstract-first extraction components
        self.abstract_extractor = AbstractFirstExtractor()
        self.pubmed_fetcher = PubMedFetcher()
        
        # Initialize two-pass extractor for hybrid mode
        self.two_pass_extractor = TwoPassExtractor(
            local_model="qwen3:14b",  # Qwen3-14B per model_evaluation.md
            cloud_model="gpt-4o-mini",
        )
        self.hybrid_mode = False  # Enable via set_hybrid_mode()
        
        # Initialize Tier 0 regex extractor for cost optimization
        self.regex_extractor = RegexExtractor()
        
        
        # Initialize sentence extractor for Excellence integration
        self.sentence_extractor = SentenceExtractor(
            provider=provider,
            model=model, # Consider using cheaper model for sentence level?
            token_tracker=self.token_tracker
        )
        
        # Initialize semantic chunker for Phase D
        self.semantic_chunker = SemanticChunker(
            client=utils.get_async_llm_client(provider=provider)
        )
        
        # Document fingerprint cache for duplicate detection
        self._fingerprint_cache: Dict[str, PipelineResult] = {}
        
        self.logger = utils.get_logger("HierarchicalPipeline")
    
    def set_hybrid_mode(self, enabled: bool = True) -> None:
        """
        Enable or disable hybrid extraction mode.
        
        When enabled, uses TwoPassExtractor for local-first extraction.
        """
        self.hybrid_mode = enabled
        self.logger.info(f"Hybrid extraction mode: {'ENABLED' if enabled else 'DISABLED'}")

    async def segment_document(self, text: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
        """
        Segment the document into logical sections using LLM-based semantic chunking (Phase D).
        """
        return await self.semantic_chunker.chunk_document_async(text, doc_id)
    
    def _compute_fingerprint(self, text: str, max_chars: int = None) -> str:
        """
        Compute document fingerprint for duplicate detection.
        
        Args:
            text: Document text
            max_chars: Max characters to use for fingerprint
            
        Returns:
            SHA256 hash of first N characters
        """
        if max_chars is None:
            max_chars = settings.CACHE_HASH_CHARS
        sample = text[:max_chars].encode('utf-8')
        return hashlib.sha256(sample).hexdigest()
    
    def _check_duplicate(self, fingerprint: str) -> Optional[PipelineResult]:
        """
        Check if document has already been processed.
        
        Args:
            fingerprint: Document fingerprint
            
        Returns:
            Cached PipelineResult if duplicate, None otherwise
        """
        if fingerprint in self._fingerprint_cache:
            self.logger.info(f"Document duplicate detected (fingerprint: {fingerprint[:8]}...)")
            return self._fingerprint_cache[fingerprint]
        return None
    
    def _cache_result(self, fingerprint: str, result: PipelineResult) -> None:
        """Cache extraction result by fingerprint."""
        self._fingerprint_cache[fingerprint] = result
    
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
    
    def _filter_and_classify(
        self, 
        document: ParsedDocument, 
        theme: str, 
        schema_fields: List[str]
    ) -> tuple:
        """
        Stage 1 & 2: Filter content and classify relevance.
        
        Args:
            document: Parsed document to process
            theme: Extraction theme
            schema_fields: List of schema field names
            
        Returns:
            Tuple of (relevant_chunks, filter_stats, relevance_stats, warnings)
        """
        warnings = []
        
        # Stage 1: Filter
        filter_result = self.content_filter.filter_chunks(document.chunks)
        filtered_chunks = filter_result.filtered_chunks
        
        if not filtered_chunks:
            warnings.append("All chunks were filtered out - using original chunks")
            filtered_chunks = document.chunks
        
        # Stage 2: Classify relevance
        relevant_chunks, relevance_results = self.relevance_classifier.get_relevant_chunks(
            filtered_chunks, theme, schema_fields
        )
        relevance_stats = self.relevance_classifier.get_classification_summary(relevance_results)
        
        if not relevant_chunks:
            warnings.append("No chunks classified as relevant - using all filtered chunks")
            relevant_chunks = filtered_chunks
            
        return relevant_chunks, filter_result.token_stats, relevance_stats, warnings
    
    def _apply_audit_penalty(
        self, 
        check_result: "CheckerResult", 
        extraction_data: Dict[str, Any], 
        evidence_dicts: List[Dict]
    ) -> "CheckerResult":
        """
        Apply quality audit penalties to check result.
        
        Args:
            check_result: Current checker result
            extraction_data: Extracted data dict
            evidence_dicts: List of evidence dicts
            
        Returns:
            Modified check_result with audit penalties applied
        """
        audit_report = self.quality_auditor.audit_extraction(extraction_data, evidence_dicts)
        
        if not audit_report.passed:
            check_result.overall_score *= 0.8  # Penalty
            check_result.passed = False
            for audit in audit_report.audits:
                if not audit.is_correct:
                    check_result.issues.append(f"Audit failed for {audit.field_name}: {audit.explanation}")
                    check_result.suggestions.append(f"For {audit.field_name}: {audit.explanation}")
        
        return check_result


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
        
        # === Tier 0: Regex Extraction ===
        self.logger.info("Tier 0: Regex extraction for structured fields...")
        regex_results = self.regex_extractor.extract_all(context)
        pre_filled_fields = {}
        for field_name, result in regex_results.items():
            if result.confidence >= settings.CONFIDENCE_THRESHOLD_MID:  # High confidence threshold
                pre_filled_fields[field_name] = result.value
                self.logger.info(f"  Regex extracted {field_name}: {result.value} (conf={result.confidence:.2f})")
        
        if pre_filled_fields:
            self.logger.info(f"  Tier 0 extracted {len(pre_filled_fields)} fields via regex")
        
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
                    pre_filled_fields=pre_filled_fields,  # Pass Tier 0 results
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
            # === NEW: Phase C Recall Boost ===
            if check_result.passed:
                missing_fields = []
                if hasattr(schema, 'model_fields'):
                    expected_fields = set(schema.model_fields.keys())
                    extracted_fields = set(extraction.data.keys())
                    for field in expected_fields:
                        val = extraction.data.get(field)
                        if val is None or val == "" or field not in extracted_fields:
                            missing_fields.append(field)
                
                if missing_fields:
                    newly_missing = []
                    for mf in missing_fields:
                        already_requested = any(mf in p for p in previous_prompts)
                        if not already_requested:
                            newly_missing.append(mf)
                    
                    if newly_missing:
                        self.logger.info(f"    Recall Boost: Detected missing fields {newly_missing}, triggering re-extraction.")
                        check_result.passed = False
                        recall_prompt = f"The following fields were missing or empty: {', '.join(newly_missing)}. Please review the text again specifically for these values."
                        check_result.suggestions.append(recall_prompt)

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
        
        # === Tier 0: Regex Extraction (Async) ===
        self.logger.info("Tier 0: Regex extraction for structured fields (async)...")
        regex_results = self.regex_extractor.extract_all(context)
        pre_filled_fields = {}
        for field_name, result in regex_results.items():
            if result.confidence >= settings.CONFIDENCE_THRESHOLD_MID:  # High confidence threshold
                pre_filled_fields[field_name] = result.value
                self.logger.info(f"  Regex extracted {field_name}: {result.value} (conf={result.confidence:.2f})")
        
        if pre_filled_fields:
            self.logger.info(f"  Tier 0 extracted {len(pre_filled_fields)} fields via regex")
        
        revision_prompts: List[str] = []
        iteration_history: List[IterationRecord] = []
        
        best_result: Optional[ExtractionWithEvidence] = None
        best_check: Optional[CheckerResult] = None
        
        for iteration in range(self.max_iterations):
            self.logger.info(f"  Iteration {iteration + 1}/{self.max_iterations} (async)...")
            
            previous_prompts = revision_prompts.copy() if revision_prompts else []
            
            try:
                # Hybrid Mode Strategy
                if self.hybrid_mode:
                    self.logger.info("    Hybrid Mode: Running parallel Sentence Extraction...")
                    
                    # 1. Start Sentence Extraction (Async) on full text
                    # We run this blindly for now, or could filter by field.
                    # Best to run concurrent with main extraction if possible?
                    # The current architecture expects 'extraction' object to proceed.
                    # Let's run sequence for now for simplicity, or gather.
                    
                    full_text = self._build_context(relevant_chunks, max_chars=100000) # Get full text
                    # Use chunks directly
                    
                    # Define complex fields to prioritize from sentence extractor
                    COMPLEX_FIELDS = {
                        "histopathology", "immunohistochemistry", "imaging_findings",
                        "presenting_symptoms", "treatment", "outcome", "diagnostic_method"
                    }
                    
                    # Run both standard and sentence extraction in parallel
                    extraction_task = self.extractor.extract_with_evidence_async(
                        context, 
                        schema, 
                        filename=document.filename,
                        revision_prompts=revision_prompts if revision_prompts else None,
                        pre_filled_fields=pre_filled_fields,  # Pass Tier 0 results
                    )
                    
                    sentence_task = self.sentence_extractor.extract(relevant_chunks)
                    
                    standard_result, sentence_frames = await asyncio.gather(extraction_task, sentence_task)
                    
                    # Merge results: Overwrite standard result with sentence result for complex fields
                    # Convert frames to evidence format
                    
                    extraction = standard_result
                    
                    # Process sentence frames
                    for frame in sentence_frames:
                        text = frame.text
                        attr = frame.content
                        field_type = attr.get("entity_type")
                        
                        if field_type and text and field_type in COMPLEX_FIELDS:
                            # Update data
                            extraction.data[field_type] = text
                            
                            # Filter out old evidence
                            extraction.evidence = [e for e in extraction.evidence if e.field_name != field_type]
                            
                            # Add new evidence with provenance
                            from .extractor import EvidenceItem
                            extraction.evidence.append(EvidenceItem(
                                field_name=field_type,
                                extracted_value=text,
                                exact_quote=text,
                                confidence=settings.CONFIDENCE_THRESHOLD_HIGH,
                                start_char=frame.start_char,
                                end_char=frame.end_char,
                                context=None
                            ))
                            
                    self.logger.info(f"    Hybrid merge complete. {len(sentence_frames)} sentence frames processed.")
                    
                else:
                    # Legacy Mode
                    extraction = await self.extractor.extract_with_evidence_async(
                        context, 
                        schema, 
                        filename=document.filename,
                        revision_prompts=revision_prompts if revision_prompts else None,
                        pre_filled_fields=pre_filled_fields,  # Pass Tier 0 results
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
            
            # === NEW: Phase C Recall Boost ===
            if check_result.passed:
                missing_fields = []
                if hasattr(schema, 'model_fields'):
                    expected_fields = set(schema.model_fields.keys())
                    extracted_fields = set(extraction.data.keys())
                    for field in expected_fields:
                        val = extraction.data.get(field)
                        if val is None or val == "" or field not in extracted_fields:
                            missing_fields.append(field)
                
                if missing_fields:
                    newly_missing = []
                    for mf in missing_fields:
                        already_requested = any(mf in p for p in previous_prompts)
                        if not already_requested:
                            newly_missing.append(mf)
                    
                    if newly_missing:
                        self.logger.info(f"    Recall Boost: Detected missing fields {newly_missing}, triggering re-extraction.")
                        check_result.passed = False
                        check_result.overall_score *= 0.9 # Penalize for incompleteness
                        recall_prompt = f"The following fields were missing or empty: {', '.join(newly_missing)}. Please review the text again specifically for these values."
                        check_result.suggestions.append(recall_prompt)

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


"""
Validation loop logic for extraction pipeline.

Handles the iterative validation and refinement process.
"""
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel
from core.parser import ParsedDocument
from core.data_types import IterationRecord

# Constants
QUALITY_AUDIT_PENALTY = 0.8  # Score penalty for failed quality audit


def _process_iteration_result(
    extraction,
    check_result,
    quality_auditor,
    iteration: int,
) -> IterationRecord:
    """
    Process iteration result with quality audit.
    
    Applies quality audit penalties and creates iteration record.
    Pure function - no I/O.
    
    Args:
        extraction: Extraction with evidence
        check_result: Checker result to potentially modify
        quality_auditor: Optional quality auditor
        iteration: Current iteration number (0-indexed)
        
    Returns:
        IterationRecord for this iteration
    """
    # Apply quality audit if available
    if quality_auditor:
        evidence_dicts = [evidence_item.model_dump() for evidence_item in extraction.evidence]
        audit_report = quality_auditor.audit_extraction(extraction.data, evidence_dicts)
        if not audit_report.passed:
            check_result.overall_score *= QUALITY_AUDIT_PENALTY
            check_result.passed = False
            for audit in audit_report.audits:
                if not audit.is_correct:
                    check_result.issues.append(
                        f"Audit failed for {audit.field_name}: {audit.explanation}"
                    )
                    check_result.suggestions.append(
                        f"For {audit.field_name}: {audit.explanation}"
                    )
    
    # Create iteration record
    return IterationRecord(
        iteration_number=iteration + 1,
        accuracy_score=check_result.accuracy_score,
        consistency_score=check_result.consistency_score,
        overall_score=check_result.overall_score,
        issues_count=len(check_result.issues),
        suggestions=check_result.suggestions,
    )


def run_validation_loop(
    context: str,
    schema: Type[BaseModel],
    extractor,  # StructuredExtractor (avoid circular import)
    checker,  # ExtractionChecker (avoid circular import)
    max_iterations: int,
    score_threshold: float,
    pre_filled: Dict[str, Any],
    document: ParsedDocument,
    relevant_chunks: List,
    theme: str,
    logger,
    regex_extractor=None,
    quality_auditor=None,
) -> Any:  # PipelineResult (avoid circular import)
    """
    Validation loop logic - sync version.
    
    Args:
        context: Extraction context text
        schema: Pydantic schema for extraction
        extractor: Extractor instance
        checker: Checker instance
        max_iterations: Maximum validation iterations
        score_threshold: Minimum score to pass
        pre_filled: Pre-filled fields from regex
        document: Source document
        relevant_chunks: Relevant document chunks
        theme: Extraction theme
        logger: Logger instance
        regex_extractor: Optional regex extractor
        quality_auditor: Optional quality auditor
        
    Returns:
        PipelineResult with extraction data
    """
    from core.pipeline.extraction.helpers import build_pipeline_result
    from core.pipeline.stages import build_revision_prompts
    
    revision_prompts: List[str] = []
    iteration_history: List[IterationRecord] = []
    
    best_result: Optional[Any] = None
    best_check: Optional[Any] = None
    
    for iteration in range(max_iterations):
        logger.info(f"  Iteration {iteration + 1}/{max_iterations}...")
        
        # Extract with evidence (sync I/O)
        try:
            extraction = extractor.extract_with_evidence(
                context,
                schema,
                filename=document.filename,
                revision_prompts=revision_prompts if revision_prompts else None,
                pre_filled_fields=pre_filled
            )
        except Exception as e:
            logger.error(f"    ERROR: {str(e)}")
            
            # Register error
            from core.error_registry import ErrorRegistry
            ErrorRegistry().register(
                e,
                location="run_validation_loop",
                context={"filename": document.filename, "iteration": iteration + 1}
            )
            continue
        
        # Validate (sync I/O)
        evidence_dicts = [evidence_item.model_dump() for evidence_item in extraction.evidence]
        check_result = checker.check(
            relevant_chunks,
            extraction.data,
            evidence_dicts,
            theme,
            threshold=score_threshold
        )
        
        # Process iteration result (apply audit, create record)
        iteration_record = _process_iteration_result(
            extraction, check_result, quality_auditor, iteration
        )
        iteration_history.append(iteration_record)
        
        # Track best result
        if best_check is None or check_result.overall_score > best_check.overall_score:
            best_result = extraction
            best_check = check_result
        
        # Check if passed
        if check_result.passed:
            logger.info(f"    ✓ Passed (score={check_result.overall_score:.2f})")
            return build_pipeline_result(
                document, extraction, check_result, iteration_history, 
                relevant_chunks, iteration + 1
            )
        
        # Build revision prompts
        logger.info(f"    ✗ Failed (score={check_result.overall_score:.2f})")
        revision_prompts = build_revision_prompts(check_result, checker)
    
    # Max iterations reached - return best result
    logger.warning(f"  Max iterations reached. Using best result (score={best_check.overall_score:.2f})")
    return build_pipeline_result(
        document, best_result, best_check, iteration_history,
        relevant_chunks, max_iterations, passed=False
    )


async def run_validation_loop_async(
    context: str,
    schema: Type[BaseModel],
    extractor,  # StructuredExtractor (avoid circular import)
    checker,  # ExtractionChecker (avoid circular import)
    max_iterations: int,
    score_threshold: float,
    pre_filled: Dict[str, Any],
    document: ParsedDocument,
    relevant_chunks: List,
    theme: str,
    logger,
    regex_extractor=None,
    quality_auditor=None,
) -> Any:  # PipelineResult (avoid circular import)
    """
    Validation loop logic - async version.
    
    Same structure as sync version, but with async I/O.
    """
    from core.pipeline.extraction.helpers import build_pipeline_result
    from core.pipeline.stages import build_revision_prompts
    
    revision_prompts: List[str] = []
    iteration_history: List[IterationRecord] = []
    
    best_result: Optional[Any] = None
    best_check: Optional[Any] = None
    
    for iteration in range(max_iterations):
        logger.info(f"  Iteration {iteration + 1}/{max_iterations} (async)...")
        
        # Extract with evidence (async I/O)
        try:
            extraction = await extractor.extract_with_evidence_async(
                context,
                schema,
                filename=document.filename,
                revision_prompts=revision_prompts if revision_prompts else None,
                pre_filled_fields=pre_filled
            )
        except Exception as e:
            logger.error(f"    ERROR: {str(e)}")
            
            # Register error
            from core.error_registry import ErrorRegistry
            ErrorRegistry().register(
                e,
                location="run_validation_loop_async",
                context={"filename": document.filename, "iteration": iteration + 1}
            )
            continue
        
        # Validate (async I/O)
        evidence_dicts = [evidence_item.model_dump() for evidence_item in extraction.evidence]
        check_result = await checker.check_async(
            relevant_chunks,
            extraction.data,
            evidence_dicts,
            theme,
            threshold=score_threshold
        )
        
        # Process iteration result (apply audit, create record)
        iteration_record = _process_iteration_result(
            extraction, check_result, quality_auditor, iteration
        )
        iteration_history.append(iteration_record)
        
        # Track best result
        if best_check is None or check_result.overall_score > best_check.overall_score:
            best_result = extraction
            best_check = check_result
        
        # Check if passed
        if check_result.passed:
            logger.info(f"    ✓ Passed (score={check_result.overall_score:.2f})")
            return build_pipeline_result(
                document, extraction, check_result, iteration_history,
                relevant_chunks, iteration + 1
            )
        
        # Build revision prompts
        logger.info(f"    ✗ Failed (score={check_result.overall_score:.2f})")
        revision_prompts = build_revision_prompts(check_result, checker)
    
    # Max iterations reached - return best result
    logger.warning(f"  Max iterations reached. Using best result (score={best_check.overall_score:.2f})")
    return build_pipeline_result(
        document, best_result, best_check, iteration_history,
        relevant_chunks, max_iterations, passed=False
    )

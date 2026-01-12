"""
Helper functions for building pipeline results.
"""
from typing import Any, List, Optional
from datetime import datetime
from core.data_types import PipelineResult, IterationRecord
from core.parser import ParsedDocument


def build_pipeline_result(
    document: ParsedDocument,
    extraction,  # ExtractionWithEvidence (avoid circular import)
    check_result,  # CheckerResult (avoid circular import)
    iteration_history: List[IterationRecord],
    relevant_chunks: List,
    iteration_count: int,
    passed: Optional[bool] = None
) -> PipelineResult:
    """
    Build a PipelineResult from extraction components.
    
    Args:
        document: Source document
        extraction: Extraction with evidence
        check_result: Checker result
        iteration_history: List of iteration records
        relevant_chunks: Relevant document chunks
        iteration_count: Number of iterations performed
        passed: Override passed status (default: use check_result.passed)
        
    Returns:
        PipelineResult instance
    """
    if passed is None:
        passed = check_result.passed
    
    return PipelineResult(
        filename=document.filename,
        extracted_data=extraction.data,
        evidence=extraction.evidence,
        passed=passed,
        quality_score=check_result.overall_score,
        accuracy_score=check_result.accuracy_score,
        consistency_score=check_result.consistency_score,
        issues=check_result.issues,
        suggestions=check_result.suggestions,
        iteration_count=iteration_count,
        iteration_history=iteration_history,
        relevant_chunks_count=len(relevant_chunks),
        timestamp=datetime.now().isoformat(),
    )


def build_failed_result(
    document: ParsedDocument,
    iteration_history: List[IterationRecord],
    error_message: str = "Extraction failed"
) -> PipelineResult:
    """
    Build a failed PipelineResult.
    
    Args:
        document: Source document
        iteration_history: List of iteration records
        error_message: Error message
        
    Returns:
        Failed PipelineResult instance
    """
    return PipelineResult(
        filename=document.filename,
        extracted_data={},
        evidence=[],
        passed=False,
        quality_score=0.0,
        accuracy_score=0.0,
        consistency_score=0.0,
        issues=[error_message],
        suggestions=[],
        iteration_count=len(iteration_history),
        iteration_history=iteration_history,
        relevant_chunks_count=0,
        timestamp=datetime.now().isoformat(),
    )

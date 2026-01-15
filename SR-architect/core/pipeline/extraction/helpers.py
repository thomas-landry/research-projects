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
    
    evidence_dicts = [e.model_dump() if hasattr(e, 'model_dump') else e for e in extraction.evidence]
    
    return PipelineResult(
        source_filename=document.filename,
        final_data=extraction.data,
        evidence=evidence_dicts,
        passed_validation=passed,
        final_overall_score=check_result.overall_score,
        final_accuracy_score=check_result.accuracy_score,
        final_consistency_score=check_result.consistency_score,
        iterations=iteration_count,
        iteration_history=iteration_history,
        content_filter_stats={},
        relevance_stats={},
        warnings=[],
        extraction_timestamp=datetime.now().isoformat(),
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
        source_filename=document.filename,
        final_data={},
        evidence=[],
        passed_validation=False,
        final_overall_score=0.0,
        final_accuracy_score=0.0,
        final_consistency_score=0.0,
        iterations=len(iteration_history),
        iteration_history=iteration_history,
        content_filter_stats={},
        relevance_stats={},
        warnings=[error_message],
        extraction_timestamp=datetime.now().isoformat(),
    )

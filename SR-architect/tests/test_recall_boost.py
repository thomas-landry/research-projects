"""
Tests for Phase C: Review-Based Self-Improvement (Recall Boost).
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from core.hierarchical_pipeline import HierarchicalExtractionPipeline
from core.parser import ParsedDocument, DocumentChunk

# Mock schema
from pydantic import BaseModel, Field

class ClinicalTrial(BaseModel):
    sample_size: str = Field(..., description="Number of patients")
    primary_outcome: str = Field(..., description="Main outcome measure")

@pytest.fixture
def mock_pipeline_recall():
    pipeline = HierarchicalExtractionPipeline(max_iterations=2)
    pipeline.extractor.extract_with_evidence_async = AsyncMock()
    pipeline.checker.check_async = AsyncMock()
    # Mock auditor to pass always
    pipeline.quality_auditor.audit_extraction_async = AsyncMock()
    
    mock_audit_report = MagicMock()
    mock_audit_report.passed = True
    mock_audit_report.audits = []
    pipeline.quality_auditor.audit_extraction_async.return_value = mock_audit_report
    
    return pipeline

@pytest.mark.asyncio
async def test_recall_boost_trigger(mock_pipeline_recall):
    """Test that missing critical fields trigger a recall boost iteration."""
    pipeline = mock_pipeline_recall
    
    # Iteration 1: Return sample_size but MISSING primary_outcome
    result1 = MagicMock()
    result1.data = {"sample_size": "100", "primary_outcome": None}
    result1.evidence = []
    
    # Iteration 2: Return BOTH (simulating success after prompt)
    result2 = MagicMock()
    result2.data = {"sample_size": "100", "primary_outcome": "Survival"}
    result2.evidence = []
    
    pipeline.extractor.extract_with_evidence_async.side_effect = [result1, result2]
    
    from core.extraction_checker import CheckerResult
    
    # Checker passes on Iteration 1 (no errors in existing data)
    check1 = CheckerResult(
        passed=True,
        suggestions=[],
        accuracy_score=1.0,
        consistency_score=1.0,
        overall_score=1.0,
        issues=[]
    )
    
    check2 = CheckerResult(
        passed=True,
        suggestions=[],
        accuracy_score=1.0,
        consistency_score=1.0,
        overall_score=1.0,
        issues=[]
    )
    
    pipeline.checker.check_async.side_effect = [check1, check2]
    
    # Doc
    doc = ParsedDocument(filename="test.pdf", chunks=[DocumentChunk(text="foo")], full_text="foo")
    
    # Execute
    result = await pipeline.extract_document_async(doc, ClinicalTrial, "theme")
    
    # Expect 2 iterations
    assert result.iterations == 2
    assert result.final_data["primary_outcome"] == "Survival"
    
    # Verify warnings or logs indicate missing field detection?
    # Or verify the PROMPT for 2nd iteration contained the missing field hint.
    # The pipeline passes `revision_prompts` to `extract_with_evidence_async`.
    
    call_args_list = pipeline.extractor.extract_with_evidence_async.call_args_list
    assert len(call_args_list) == 2
    
    # Check 2nd call arguments
    second_call_kwargs = call_args_list[1].kwargs
    revision_prompts = second_call_kwargs.get("revision_prompts")
    assert revision_prompts is not None
    # We expect something like "Missing field: primary_outcome"
    assert any("primary_outcome" in p for p in revision_prompts)

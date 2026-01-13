"""
Integration tests for HierarchicalExtractionPipeline.

These tests verify the pipeline end-to-end with mocked LLM clients.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.hierarchical_pipeline import HierarchicalExtractionPipeline, PipelineResult
from core.parser import DocumentParser, ParsedDocument, DocumentChunk
from pydantic import BaseModel, Field
from typing import List
import os


# Define a simple schema for testing
class IntegrationTestSchema(BaseModel):
    patient_age: int = Field(description="Age of the patient")
    diagnosis: str = Field(description="Primary diagnosis")


def _create_mock_completion(prompt_tokens=100, completion_tokens=50):
    """Helper to create mock completion objects with usage stats."""
    mock_completion = MagicMock()
    mock_completion.usage = MagicMock()
    mock_completion.usage.prompt_tokens = prompt_tokens
    mock_completion.usage.completion_tokens = completion_tokens
    mock_completion.usage.total_tokens = prompt_tokens + completion_tokens
    return mock_completion


def test_pipeline_integration_full_flow():
    """
    Test the HierarchicalExtractionPipeline end-to-end with a real-ish flow.
    We mock the LLM client but keep the pipeline logic intact.
    """
    from core.relevance_classifier import RelevanceResponse, ChunkRelevance
    from core.validation.models import CheckerResponse
    from core.extractor import EvidenceItem
    from agents.quality_auditor import FieldAudit
    
    mock_relevance_resp = RelevanceResponse(classifications=[
        ChunkRelevance(index=0, relevant=1, reason="Found keywords")
    ])
    
    mock_extraction = IntegrationTestSchema(patient_age=45, diagnosis="Test Condition")
    
    mock_checker_resp = CheckerResponse(
        accuracy_score=0.95,
        consistency_score=0.95,
        issues=[],
        suggestions=[]
    )
    
    mock_evidence_resp = MagicMock()
    mock_evidence_resp.evidence = [
        EvidenceItem(field_name="patient_age", extracted_value=45, exact_quote="45-year-old male", confidence=1.0),
        EvidenceItem(field_name="diagnosis", extracted_value="Test Condition", exact_quote="Final diagnosis was Test Condition", confidence=1.0)
    ]
    
    mock_audit = FieldAudit(
        field_name="patient_age",
        is_correct=True,
        confidence=1.0,
        explanation="Matches text",
        severity="low"
    )
    
    mock_client = MagicMock()
    mock_completion = _create_mock_completion()
    
    def side_effect(*args, **kwargs):
        resp_model = kwargs.get("response_model")
        name = str(resp_model)
        
        if "RelevanceResponse" in name:
            return (mock_relevance_resp, mock_completion)
        if "CheckerResponse" in name:
            return (mock_checker_resp, mock_completion)
        if "EvidenceResponse" in name or "evidence" in name.lower():
            return (mock_evidence_resp, mock_completion)
        if "FieldAudit" in name:
            return (mock_audit, mock_completion)
        return (mock_extraction, mock_completion)
    
    mock_client.chat.completions.create_with_completion.side_effect = side_effect
    mock_client.chat.completions.create.side_effect = lambda *args, **kwargs: side_effect(*args, **kwargs)[0]
    
    with patch("core.utils.get_llm_client", return_value=mock_client):
        with patch("core.utils.LLMCache") as MockCache:
            MockCache.return_value.get.return_value = None
            
            pipeline = HierarchicalExtractionPipeline(
                provider="openai",
                model="gpt-4o",
                score_threshold=0.8,
                max_iterations=1,
                verbose=True
            )
            
            sample_text = """
            CASE REPORT: A 45-year-old male presented with respiratory distress.
            Final diagnosis was Test Condition.
            """
            
            result = pipeline.extract_from_text(
                text=sample_text,
                schema=IntegrationTestSchema,
                theme="patient demographics",
                filename="test_paper.pdf"
            )
            
            assert isinstance(result, PipelineResult)
            assert result.final_data["patient_age"] == 45
            assert result.final_data["diagnosis"] == "Test Condition"


@pytest.mark.skip(reason="Requires precise mock orchestration across multiple pipeline stages")
def test_pipeline_with_real_pdf_parsing():
    """Verify that we can parse a real PDF and pass it through the pipeline (mocked LLM)."""
    from core.relevance_classifier import RelevanceResponse, ChunkRelevance
    from core.validation.models import CheckerResponse
    from core.extractor import EvidenceItem
    from agents.quality_auditor import FieldAudit
    
    parser = DocumentParser()
    doc = parser.parse_pdf("tests/data/sample.pdf")
    assert len(doc.chunks) > 0
    
    mock_client = MagicMock()
    mock_completion = _create_mock_completion()
    
    mock_ev = MagicMock()
    mock_ev.evidence = [EvidenceItem(field_name="patient_age", extracted_value=50, exact_quote="50", confidence=1.0)]
    
    responses = [
        (RelevanceResponse(classifications=[ChunkRelevance(index=i, relevant=1, reason="Relevant") for i in range(10)]), mock_completion),
        (IntegrationTestSchema(patient_age=50, diagnosis="Meningotheliomatosis"), mock_completion),
        (mock_ev, mock_completion),
        (CheckerResponse(accuracy_score=1.0, consistency_score=1.0, issues=[], suggestions=[]), mock_completion),
        (FieldAudit(field_name="patient_age", is_correct=True, confidence=1.0, explanation="OK", severity="low"), mock_completion),
    ]
    
    call_count = [0]
    def side_effect(*args, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]
    
    mock_client.chat.completions.create_with_completion.side_effect = side_effect
    mock_client.chat.completions.create.side_effect = lambda *a, **kw: side_effect(*a, **kw)[0]
    
    with patch("core.utils.get_llm_client", return_value=mock_client):
        with patch("core.utils.LLMCache") as MockCache:
            MockCache.return_value.get.return_value = None
            
            pipeline = HierarchicalExtractionPipeline(max_iterations=1)
            
            result = pipeline.extract_document(
                document=doc,
                schema=IntegrationTestSchema,
                theme="meningotheliomatosis"
            )
            
            assert result.passed_validation is True
            assert result.final_data["patient_age"] == 50


@pytest.mark.skip(reason="Async extraction path requires comprehensive async mock setup")
def test_pipeline_async_integration():
    """Verify the async extraction path.
    
    NOTE: This test is skipped because the async mocking requires a more
    sophisticated setup to properly mock multiple awaited calls.
    """
    pass

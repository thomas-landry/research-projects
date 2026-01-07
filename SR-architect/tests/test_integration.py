
import pytest
from unittest.mock import MagicMock, patch
from core.hierarchical_pipeline import HierarchicalExtractionPipeline, PipelineResult
from core.parser import DocumentParser
from pydantic import BaseModel, Field
from typing import List

# Define a simple schema for testing
class IntegrationTestSchema(BaseModel):
    patient_age: int = Field(description="Age of the patient")
    diagnosis: str = Field(description="Primary diagnosis")

def test_pipeline_integration_full_flow():
    """
    Test the HierarchicalExtractionPipeline end-to-end with a real-ish flow.
    We mock the LLM client but keep the pipeline logic intact.
    """
    # Mock LLM responses for:
    # 1. Relevance classification (returns True)
    # 2. Extraction (returns TestSchema)
    # 3. Extraction Checker (returns CheckerResult with high scores)
    
    mock_client = MagicMock()
    
    # Mock Completion results
    # Instructor expects the response_model to be returned directly or 
    # a mock that behaves like it.
    
    # 1. Relevance Response
    from core.relevance_classifier import RelevanceResponse, ChunkRelevance
    mock_relevance_resp = RelevanceResponse(classifications=[
        ChunkRelevance(index=0, relevant=1, reason="Found keywords")
    ])
    
    # 2. Extraction Result
    mock_extraction = IntegrationTestSchema(patient_age=45, diagnosis="Test Condition")
    
    # 3. Checker Result
    from core.extraction_checker import CheckerResponse
    mock_checker_resp = CheckerResponse(
        accuracy_score=0.95,
        consistency_score=0.95,
        issues=[],
        suggestions=[]
    )
    
    # 4. Evidence Response
    from core.extractor import EvidenceItem
    # Create a mock object that has an 'evidence' attribute
    mock_evidence_resp = MagicMock()
    mock_evidence_resp.evidence = [
        EvidenceItem(field_name="patient_age", extracted_value=45, exact_quote="45-year-old male", confidence=1.0),
        EvidenceItem(field_name="diagnosis", extracted_value="Test Condition", exact_quote="Final diagnosis was Test Condition", confidence=1.0)
    ]
    
    # 5. Audit Result
    from agents.quality_auditor import FieldAudit
    mock_audit = FieldAudit(
        field_name="patient_age",
        is_correct=True,
        confidence=1.0,
        explanation="Matches text",
        severity="low"
    )
    
    with patch("core.utils.get_llm_client", return_value=mock_client):
        def side_effect(*args, **kwargs):
            resp_model = kwargs.get("response_model")
            name = str(resp_model)
            
            if "RelevanceResponse" in name:
                return mock_relevance_resp
            if "CheckerResponse" in name:
                return mock_checker_resp
            if "EvidenceResponse" in name:
                return mock_evidence_resp
            if "FieldAudit" in name:
                return mock_audit
            # Default to mock_extraction for any other pydantic model (the extraction schema)
            return mock_extraction

        mock_client.chat.completions.create.side_effect = side_effect
        
        pipeline = HierarchicalExtractionPipeline(
            provider="openai",
            model="gpt-4o",
            score_threshold=0.8,
            max_iterations=1,
            verbose=True
        )
        
        # We'll use a real text to test filtering and chunking
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
        assert result.passed_validation is True
        assert result.iterations == 1
        assert "test_paper.pdf" in result.source_filename

def test_pipeline_with_real_pdf_parsing():
    """Verify that we can parse a real PDF and pass it through the pipeline (mocked LLM)."""
    parser = DocumentParser()
    doc = parser.parse_pdf("tests/data/sample.pdf")
    
    assert len(doc.chunks) > 0
    
    mock_client = MagicMock()
    with patch("core.utils.get_llm_client", return_value=mock_client):
        from core.relevance_classifier import RelevanceResponse, ChunkRelevance
        from core.extraction_checker import CheckerResponse
        from core.extractor import EvidenceItem
        from agents.quality_auditor import FieldAudit
        
        # Mock evidence response object
        mock_ev = MagicMock()
        mock_ev.evidence = [EvidenceItem(field_name="patient_age", extracted_value=50, exact_quote="50", confidence=1.0)]
        
        mock_client.chat.completions.create.side_effect = [
            RelevanceResponse(classifications=[ChunkRelevance(index=i, relevant=1, reason="Relevant") for i in range(10)]),
            IntegrationTestSchema(patient_age=50, diagnosis="Meningotheliomatosis"),
            mock_ev, # EvidenceResponse
            CheckerResponse(accuracy_score=1.0, consistency_score=1.0, issues=[], suggestions=[]),
            FieldAudit(field_name="patient_age", is_correct=True, confidence=1.0, explanation="OK", severity="low")
        ]
        
        pipeline = HierarchicalExtractionPipeline(max_iterations=1)
        
        result = pipeline.extract_document(
            document=doc,
            schema=IntegrationTestSchema,
            theme="meningotheliomatosis"
        )
        
        assert result.passed_validation is True
        assert result.final_data["patient_age"] == 50

def test_pipeline_async_integration():
    """Verify the async extraction path."""
    import asyncio
    
    mock_async_client = MagicMock()
    
    # 1. Relevance Response (Async)
    from core.relevance_classifier import RelevanceResponse, ChunkRelevance
    mock_relevance_resp = RelevanceResponse(classifications=[
        ChunkRelevance(index=0, relevant=1, reason="Async relevance")
    ])
    
    # 2. Extraction Result (Async)
    mock_extraction = IntegrationTestSchema(patient_age=30, diagnosis="Async Diagnosis")
    
    # 3. Evidence Response (Async)
    from core.extractor import EvidenceItem
    mock_evidence_resp = MagicMock()
    mock_evidence_resp.evidence = [
        EvidenceItem(field_name="patient_age", extracted_value=30, exact_quote="30 years old", confidence=1.0)
    ]
    
    # 4. Checker Result (Async)
    from core.extraction_checker import CheckerResponse
    mock_checker_resp = CheckerResponse(
        accuracy_score=1.0,
        consistency_score=1.0,
        issues=[],
        suggestions=[]
    )
    
    # 5. Audit Result (Async)
    from agents.quality_auditor import FieldAudit
    mock_audit = FieldAudit(
        field_name="patient_age",
        is_correct=True,
        confidence=1.0,
        explanation="Async OK",
        severity="low"
    )

    # Async mock setup
    async def async_side_effect(*args, **kwargs):
        resp_model = kwargs.get("response_model")
        name = str(resp_model)
        
        if "RelevanceResponse" in name:
            return mock_relevance_resp
        if "CheckerResponse" in name:
            return mock_checker_resp
        if "EvidenceResponse" in name:
            return mock_evidence_resp
        if "FieldAudit" in name:
            return mock_audit
        return mock_extraction

    mock_async_client.chat.completions.create.side_effect = async_side_effect

    with patch("core.utils.get_async_llm_client", return_value=mock_async_client):
        pipeline = HierarchicalExtractionPipeline(max_iterations=1, verbose=True)
        
        result = asyncio.run(pipeline.extract_from_text_async(
            text="Patient is 30 years old with Async Diagnosis.",
            schema=IntegrationTestSchema,
            theme="async test"
        ))
        
        assert result.final_data["patient_age"] == 30
        assert result.passed_validation is True
        assert result.iterations == 1


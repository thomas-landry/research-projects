"""
Integration tests for HierarchicalExtractionPipeline with SentenceExtractor.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from core.hierarchical_pipeline import HierarchicalExtractionPipeline
from core.parser import ParsedDocument, DocumentChunk

# Mock schema
from pydantic import BaseModel, Field

class CaseReport(BaseModel):
    patient_age: str = Field(..., description="Age")
    histopathology: str = Field(..., description="Pathology findings")

from core.data_types import EvidenceFrame

@pytest.fixture
def mock_pipeline():
    with patch('core.hierarchical_pipeline.SentenceExtractor') as MockSentenceExtractor:
        # Setup mock instance
        mock_instance = AsyncMock()
        mock_instance.extract.return_value = [
            EvidenceFrame(
                text="Spindle cell neoplasm", 
                doc_id="test.pdf",
                start_char=20,
                end_char=41,
                content={"entity_type": "histopathology"}
            )
        ]
        MockSentenceExtractor.return_value = mock_instance
        
        pipeline = HierarchicalExtractionPipeline()
        pipeline.sentence_extractor = mock_instance # Inject manually if needed or rely on init
        return pipeline, mock_instance

@pytest.mark.asyncio
async def test_sentence_extraction_integration(mock_pipeline):
    """Test that pipeline calls sentence extractor for complex fields."""
    pipeline, mock_sent_ext = mock_pipeline
    
    # Enable hybrid/sentence mode
    pipeline.set_hybrid_mode(True)
    
    # Mock legacy extractor to return partial data (age only)
    pipeline.extractor.extract_with_evidence_async = AsyncMock()
    mock_legacy_result = MagicMock()
    mock_legacy_result.data = {"patient_age": "45"}
    mock_legacy_result.evidence = [] 
    pipeline.extractor.extract_with_evidence_async.return_value = mock_legacy_result
    
    # Create dummy doc
    doc = ParsedDocument(
        filename="test.pdf",
        chunks=[DocumentChunk(text="Patient is 45. Pathology showed spindle cell neoplasm.")],
        full_text="..."
    )
    
    # Run extraction
    result = await pipeline.extract_document_async(doc, CaseReport, "medical theme")
    
    # Verify legacy extractor called
    assert pipeline.extractor.extract_with_evidence_async.called
    
    # Verify sentence extractor called
    assert mock_sent_ext.extract.called
    
    # Verify results merged
    # Age from legacy, Histopathology from sentence extractor
    assert result.final_data["patient_age"] == "45"
    assert result.final_data["histopathology"] == "Spindle cell neoplasm"

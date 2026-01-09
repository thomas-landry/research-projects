"""
Tests for Phase E: Structured Evidence Frames (Provenance).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.sentence_extractor import SentenceExtractor
from core.data_types import EvidenceFrame
from core.parser import DocumentChunk

@pytest.fixture
def mock_llm_client_provenance():
    client = MagicMock()
    mock_create = AsyncMock()
    # Mock LLM returning a valid entity
    mock_create.return_value.choices[0].message.content = json.dumps([
        {
            "entity_text": "52-year-old female",
            "attr": {"entity_type": "patient_demographics"}
        }
    ])
    client.chat.completions.create = mock_create
    return client

import json

@pytest.mark.asyncio
async def test_sentence_extractor_returns_frames(mock_llm_client_provenance):
    """Test that extractor returns EvidenceFrame objects with correct indices."""
    
    with patch('core.sentence_extractor.get_async_llm_client', return_value=mock_llm_client_provenance):
        extractor = SentenceExtractor(provider="mock")
        
        # Text setup
        # "We report a case..." is at index 0
        # "52-year-old female" starts at index 28
        text = "We report a case of a 52-year-old female presenting with dyspnea."
        chunk = DocumentChunk(
            text=text,
            source_file="test_doc.pdf",
            section="Abstract"
        )
        
        # Override tokenizer to ensure deterministic sentence split for test
        # Just treats whole text as one sentence
        extractor._tokenize_sentences = lambda t: [t] 
        
        results = await extractor.extract([chunk])
        
        assert len(results) > 0
        frame = results[0]
        
        # Check Type
        assert isinstance(frame, EvidenceFrame)
        
        # Check Content
        assert frame.text == "52-year-old female"
        assert frame.doc_id == "test_doc.pdf"
        
        # Check Indices
        # "We report a case of a " is 22 chars
        # "52-year-old female"
        expected_start = text.find("52-year-old female")
        assert expected_start > 0
        
        assert frame.start_char == expected_start
        assert frame.end_char == expected_start + len("52-year-old female")
        
        # Check structured content
        assert frame.content["entity_type"] == "patient_demographics"

@pytest.mark.asyncio
async def test_provenance_multiple_sentences(mock_llm_client_provenance):
    """Test offsets with multiple sentences."""
    # ... can expand later
    pass

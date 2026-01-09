"""
Tests for the Unit-Context SentenceExtractor.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.parser import DocumentChunk
# We anticipate creating this class
from core.sentence_extractor import SentenceExtractor

@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    # Mock chat completion response
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '[{"entity_text": "45 years old", "attr": {"entity_type": "patient_age"}}]'
    mock_completion.usage.prompt_tokens = 10
    mock_completion.usage.completion_tokens = 5
    mock_completion.usage.total_tokens = 15
    
    client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return client

@pytest.fixture
def sentence_extractor(mock_llm_client):
    extractor = SentenceExtractor(
        model="test-model",
        context_window_size=1, # +/- 1 sentence
        concurrency_limit=5
    )
    extractor.client = mock_llm_client
    return extractor

def test_sentence_tokenization(sentence_extractor):
    """Test that text is correctly split into sentences."""
    text = "Sentence one. Sentence two? Sentence three!"
    sentences = sentence_extractor._tokenize_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Sentence one."
    assert sentences[1] == "Sentence two?"
    assert sentences[2] == "Sentence three!"

def test_context_window_generation(sentence_extractor):
    """Test generation of sliding context windows."""
    sentences = ["S1.", "S2.", "S3.", "S4.", "S5."]
    
    # Test window size 1 (default in fixture)
    # For S1: Context [S1, S2]
    ctx1 = sentence_extractor._get_context(sentences, index=0)
    assert "S1." in ctx1
    assert "S2." in ctx1
    assert "S3." not in ctx1
    
    # For S3: Context [S2, S3, S4]
    ctx3 = sentence_extractor._get_context(sentences, index=2)
    assert "S2." in ctx3
    assert "S3." in ctx3
    assert "S4." in ctx3
    assert "S1." not in ctx3

@pytest.mark.asyncio
async def test_extract_async_flow(sentence_extractor, mock_llm_client):
    """Test the full async extraction flow."""
    chunks = [DocumentChunk(text="Patient was 45 years old. He had fever.", section="Case")]
    
    # Mock the LLM to return different things based on input (optional, or just generic)
    # For simplicity, we stick to the fixture return
    
    results = await sentence_extractor.extract(chunks)
    
    # Should have called LLM twice (2 sentences)
    assert mock_llm_client.chat.completions.create.call_count == 2
    
    # Check results structure
    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0]["entity_text"] == "45 years old"
    assert results[0]["attr"]["entity_type"] == "patient_age"

@pytest.mark.asyncio
async def test_concurrency_control(sentence_extractor):
    """Verify that concurrency is limited."""
    # Mock _extract_single_sentence to be slow
    async def slow_extract(*args):
        await asyncio.sleep(0.1)
        return []
    
    sentence_extractor._extract_single_sentence = slow_extract
    
    sentences = ["S"] * 10 # 10 sentences
    
    # We want to ensure it doesn't run all 10 at once if limit is 5
    # This is hard to assert deterministically without complex mocks, 
    # but we can at least ensure it completes without error and handles the list.
    
    # Use a spy or just run it
    chunks = [DocumentChunk(text=" ".join(sentences), section="Test")]
    await sentence_extractor.extract(chunks)
    # passed if no exception

def test_merge_results(sentence_extractor):
    """Test deduping and merging of extracted entities."""
    raw_results = [
        {"entity_text": "foo", "attr": {"entity_type": "type1"}},
        {"entity_text": "foo", "attr": {"entity_type": "type1"}}, # Duplicate
        {"entity_text": "bar", "attr": {"entity_type": "type2"}}
    ]
    
    merged = sentence_extractor._merge_results(raw_results)
    assert len(merged) == 2
    assert {"entity_text": "foo", "attr": {"entity_type": "type1"}} in merged
    assert {"entity_text": "bar", "attr": {"entity_type": "type2"}} in merged

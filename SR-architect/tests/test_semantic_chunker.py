"""
Tests for SemanticChunker (Phase D).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.semantic_chunker import SemanticChunker
from core.parser import DocumentChunk

@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    # Mock chat.completions.create as AsyncMock for await support
    mock_create = AsyncMock()
    mock_create.return_value.choices[0].message.content = '[]'
    client.chat.completions.create = mock_create
    
    # Also mock create_async if checking existence
    client.chat.completions.create_async = AsyncMock()
    
    return client

@pytest.mark.asyncio
async def test_semantic_chunking_logic(mock_llm_client):
    """
    Test that the chunker correctly splits text based on LLM-returned anchors.
    """
    chunker = SemanticChunker(client=mock_llm_client)
    
    text = """
    Abstract
    This is the abstract.
    
    Methods
    This is the methods section.
    
    Results
    This is the results section.
    
    Discussion
    This is the discussion.
    """
    
    # Mock LLM response with proper JSON anchors
    # Logic: Splits occur AT the anchor text.
    # To get "Methods" section, we need anchors for "Methods" and "Results".
    # Chunk 1: Start -> Methods (Abstract)
    # Chunk 2: Methods -> Results (Methods)
    # Chunk 3: Results -> Discussion (Results)
    # Chunk 4: Discussion -> End (Discussion)
    
    mock_response_json = """
    [
        {"title": "Methods", "anchor_text": "Methods"},
        {"title": "Results", "anchor_text": "Results"},
        {"title": "Discussion", "anchor_text": "Discussion"}
    ]
    """
    
    # Setup mock to return this JSON
    # We patch the 'extract_json' utility or the client response?
    # Better to mock the client response text if we can trust extract_json (which we verified).
    
    chunker.client.chat.completions.create.return_value.choices[0].message.content = mock_response_json
    
    # We'll use a mocked internal _query_llm to simplify test if needed, 
    # but let's try testing the public method with a mocked client.
    
    chunks = await chunker.chunk_document_async(text, doc_id="test_doc")
    
    assert len(chunks) == 4
    
    # Check Chunk 1 (Abstract)
    assert chunks[0].section == "Intro/Abstract" # Default label for first chunk?
    assert "This is the abstract" in chunks[0].text
    
    # Check Chunk 2 (Methods)
    assert chunks[1].section == "Methods"
    assert "This is the methods section" in chunks[1].text
    
    # Check Chunk 3 (Results)
    assert chunks[2].section == "Results"
    assert "This is the results section" in chunks[2].text
    
    # Check Chunk 4 (Discussion)
    assert chunks[3].section == "Discussion"
    assert "This is the discussion" in chunks[3].text

@pytest.mark.asyncio
async def test_semantic_chunking_fallback():
    """Test fallback when LLM returns nothing or fails."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = "[]" # Empty list
    
    chunker = SemanticChunker(client=mock_client)
    text = "Just some text."
    
    chunks = await chunker.chunk_document_async(text)
    
    # Should return single chunk as fallback
    assert len(chunks) == 1
    assert chunks[0].text == text

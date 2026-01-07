
import pytest
from core.text_splitter import TextSplitter, split_text_into_chunks

def test_split_text_basic():
    """Test basic splitting functionality."""
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    # Small chunk size to force split
    splitter = TextSplitter(chunk_size=20, chunk_overlap=0)
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 1
    assert "Paragraph 1." in chunks
    assert "Paragraph 2." in chunks

def test_split_text_with_overlap():
    """Test splitting with overlap."""
    text = "1234567890"
    splitter = TextSplitter(chunk_size=5, chunk_overlap=2)
    chunks = splitter.split_text(text)
    
    # Expected: "12345", "45678", "7890" roughly
    assert len(chunks) >= 2
    # Check for overlap (naive check)
    assert chunks[0] == "12345"
    assert "45" in chunks[1]

def test_split_text_into_chunks_helper():
    """Test the helper function."""
    text = "A long text that should be split." * 10
    chunks = split_text_into_chunks(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 50 for c in chunks)

def test_empty_input():
    """Test empty input handling."""
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks(None) == []


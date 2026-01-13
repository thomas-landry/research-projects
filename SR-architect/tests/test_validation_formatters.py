"""
Tests for validation formatters.

TDD RED PHASE: These tests will FAIL because core/validation/formatters.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from core.validation.formatters import (
    format_source_text,
    format_extracted_data,
    format_evidence
)
from core.parser import DocumentChunk


class TestFormatSourceText:
    """Test source text formatting for checker prompts."""
    
    def test_format_single_chunk(self):
        """Should format single chunk with section label."""
        chunks = [
            DocumentChunk(
                text="Sample text from the paper.",
                page_number=1,
                chunk_index=0,
                section="Methods"
            )
        ]
        result = format_source_text(chunks)
        
        assert "Chunk 0" in result
        assert "[Methods]" in result
        assert "Sample text from the paper." in result
    
    def test_format_multiple_chunks(self):
        """Should format multiple chunks with separators."""
        chunks = [
            DocumentChunk(text="First chunk", page_number=1, chunk_index=0, section="Abstract"),
            DocumentChunk(text="Second chunk", page_number=2, chunk_index=1, section="Methods")
        ]
        result = format_source_text(chunks)
        
        assert "Chunk 0" in result
        assert "Chunk 1" in result
        assert "First chunk" in result
        assert "Second chunk" in result
        assert "[Abstract]" in result
        assert "[Methods]" in result
    
    def test_format_chunk_without_section(self):
        """Should handle chunks without section labels."""
        chunks = [
            DocumentChunk(text="Text without section", page_number=1, chunk_index=0)
        ]
        result = format_source_text(chunks)
        
        assert "Text without section" in result
        assert "Chunk 0" in result
    
    def test_format_respects_max_chars(self):
        """Should truncate to max_chars limit."""
        long_text = "A" * 5000
        chunks = [
            DocumentChunk(text=long_text, page_number=1, chunk_index=0),
            DocumentChunk(text="This should not appear", page_number=2, chunk_index=1)
        ]
        result = format_source_text(chunks, max_chars=5050)  # Just enough for first chunk + header
        
        # Should include first chunk but not second
        assert "AAAA" in result
        assert "This should not appear" not in result
        assert len(result) <= 5100  # Allow for headers


class TestFormatExtractedData:
    """Test extracted data formatting."""
    
    def test_format_simple_dict(self):
        """Should format dict as readable key-value pairs."""
        data = {
            "doi": "10.1234/test",
            "year": 2024,
            "sample_size": 42
        }
        result = format_extracted_data(data)
        
        assert "doi" in result
        assert "10.1234/test" in result
        assert "year" in result
        assert "2024" in result
        assert "sample_size" in result
        assert "42" in result
    
    def test_format_excludes_quote_fields(self):
        """Should exclude fields ending with '_quote'."""
        data = {
            "doi": "10.1234/test",
            "doi_quote": "This is the quote",  # Should be excluded
            "year": 2024
        }
        result = format_extracted_data(data)
        
        assert "doi:" in result or "doi" in result
        assert "10.1234/test" in result
        assert "doi_quote" not in result
        assert "This is the quote" not in result
    
    def test_format_excludes_private_fields(self):
        """Should exclude fields starting with '_'."""
        data = {
            "doi": "10.1234/test",
            "_internal": "private data",  # Should be excluded
            "year": 2024
        }
        result = format_extracted_data(data)
        
        assert "doi" in result
        assert "_internal" not in result
        assert "private data" not in result
    
    def test_format_empty_dict(self):
        """Should handle empty dict gracefully."""
        data = {}
        result = format_extracted_data(data)
        
        assert isinstance(result, str)
        # Should return empty or minimal output
        assert len(result) < 10


class TestFormatEvidence:
    """Test evidence formatting."""
    
    def test_format_single_evidence(self):
        """Should format single evidence item."""
        evidence = [
            {
                "field_name": "doi",
                "extracted_value": "10.1234/test",
                "exact_quote": "DOI: 10.1234/test",
                "confidence": 0.95
            }
        ]
        result = format_evidence(evidence)
        
        assert "doi" in result
        assert "10.1234/test" in result
        assert "DOI: 10.1234/test" in result
        assert "0.95" in result or "95" in result
    
    def test_format_multiple_evidence(self):
        """Should format multiple evidence items."""
        evidence = [
            {
                "field_name": "doi",
                "extracted_value": "10.1234/test",
                "exact_quote": "DOI: 10.1234/test",
                "confidence": 0.95
            },
            {
                "field_name": "year",
                "extracted_value": 2024,
                "exact_quote": "Published in 2024",
                "confidence": 0.9
            }
        ]
        result = format_evidence(evidence)
        
        assert "doi" in result
        assert "year" in result
        assert "10.1234/test" in result
        assert "2024" in result
    
    def test_format_empty_evidence(self):
        """Should handle empty evidence list."""
        evidence = []
        result = format_evidence(evidence)
        
        assert isinstance(result, str)
        assert "No evidence" in result or len(result) < 50
    
    def test_format_evidence_with_missing_fields(self):
        """Should handle evidence items with missing optional fields."""
        evidence = [
            {
                "field_name": "doi",
                "extracted_value": "10.1234/test"
                # Missing exact_quote and confidence
            }
        ]
        result = format_evidence(evidence)
        
        # Should still format without errors
        assert "doi" in result
        assert "10.1234/test" in result

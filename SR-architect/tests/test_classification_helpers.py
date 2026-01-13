"""
Tests for classification helper functions.

TDD RED PHASE: These tests will FAIL because core/classification/helpers.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from core.classification.helpers import truncate_chunk, build_batch_prompt
from core.parser import DocumentChunk


class TestTruncateChunk:
    """Test truncate_chunk helper function."""
    
    def test_truncate_long_chunk(self):
        """Should truncate chunk text to preview_chars with ellipsis."""
        chunk = DocumentChunk(text="A" * 1000, source_file="test.pdf")
        result = truncate_chunk(chunk, preview_chars=100)
        
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")
        assert result.startswith("AAA")
    
    def test_no_truncate_short_chunk(self):
        """Should not truncate if text is shorter than limit."""
        chunk = DocumentChunk(text="Short text", source_file="test.pdf")
        result = truncate_chunk(chunk, preview_chars=100)
        
        assert result == "Short text"
        assert not result.endswith("...")
    
    def test_truncate_exact_length(self):
        """Should not truncate if text is exactly preview_chars."""
        text = "A" * 100
        chunk = DocumentChunk(text=text, source_file="test.pdf")
        result = truncate_chunk(chunk, preview_chars=100)
        
        assert result == text
        assert not result.endswith("...")
    
    def test_truncate_strips_whitespace(self):
        """Should strip leading/trailing whitespace before truncating."""
        chunk = DocumentChunk(text="  \n  Text content  \n  ", source_file="test.pdf")
        result = truncate_chunk(chunk, preview_chars=100)
        
        assert result == "Text content"
        assert not result.startswith(" ")
        assert not result.endswith(" ")
    
    def test_truncate_empty_chunk(self):
        """Should handle empty chunk text."""
        chunk = DocumentChunk(text="", source_file="test.pdf")
        result = truncate_chunk(chunk, preview_chars=100)
        
        assert result == ""


class TestBuildBatchPrompt:
    """Test build_batch_prompt helper function."""
    
    def test_build_batch_prompt_basic(self):
        """Should build prompt with chunks, theme, and fields."""
        chunks = [
            DocumentChunk(text="Patient was 45 years old", source_file="test.pdf"),
            DocumentChunk(text="References section", source_file="test.pdf")
        ]
        
        prompt = build_batch_prompt(
            chunks=chunks,
            start_index=0,
            theme="patient demographics",
            schema_fields=["age", "gender"],
            preview_chars=100
        )
        
        # Should contain theme
        assert "patient demographics" in prompt.lower()
        
        # Should contain fields
        assert "age" in prompt.lower()
        assert "gender" in prompt.lower()
        
        # Should contain chunk markers
        assert "[0]" in prompt
        assert "[1]" in prompt
        
        # Should contain chunk text
        assert "Patient was 45 years old" in prompt
        assert "References section" in prompt
    
    def test_build_batch_prompt_with_sections(self):
        """Should include section information when available."""
        chunks = [
            DocumentChunk(text="Methods text", source_file="test.pdf", section="Methods"),
            DocumentChunk(text="Results text", source_file="test.pdf", section="Results")
        ]
        
        prompt = build_batch_prompt(
            chunks=chunks,
            start_index=0,
            theme="test theme",
            schema_fields=["field1"],
            preview_chars=100
        )
        
        # Should include section labels
        assert "Methods" in prompt
        assert "Results" in prompt
    
    def test_build_batch_prompt_start_index(self):
        """Should use start_index for chunk numbering."""
        chunks = [
            DocumentChunk(text="Chunk A", source_file="test.pdf"),
            DocumentChunk(text="Chunk B", source_file="test.pdf")
        ]
        
        prompt = build_batch_prompt(
            chunks=chunks,
            start_index=5,
            theme="test",
            schema_fields=["field1"],
            preview_chars=100
        )
        
        # Should start numbering at 5
        assert "[5]" in prompt
        assert "[6]" in prompt
        assert "[0]" not in prompt
    
    def test_build_batch_prompt_truncates_chunks(self):
        """Should truncate long chunks using preview_chars."""
        long_text = "A" * 1000
        chunks = [
            DocumentChunk(text=long_text, source_file="test.pdf")
        ]
        
        prompt = build_batch_prompt(
            chunks=chunks,
            start_index=0,
            theme="test",
            schema_fields=["field1"],
            preview_chars=50
        )
        
        # Should contain truncated version with ellipsis
        assert "..." in prompt
        # Should not contain full 1000 A's
        assert "A" * 1000 not in prompt
    
    def test_build_batch_prompt_multiple_fields(self):
        """Should list all schema fields."""
        chunks = [DocumentChunk(text="Test", source_file="test.pdf")]
        
        prompt = build_batch_prompt(
            chunks=chunks,
            start_index=0,
            theme="test theme",
            schema_fields=["age", "gender", "treatment", "outcome"],
            preview_chars=100
        )
        
        # Should contain all fields
        assert "age" in prompt
        assert "gender" in prompt
        assert "treatment" in prompt
        assert "outcome" in prompt
    
    def test_build_batch_prompt_empty_chunks(self):
        """Should handle empty chunk list."""
        prompt = build_batch_prompt(
            chunks=[],
            start_index=0,
            theme="test",
            schema_fields=["field1"],
            preview_chars=100
        )
        
        # Should still have theme and fields
        assert "test" in prompt
        assert "field1" in prompt

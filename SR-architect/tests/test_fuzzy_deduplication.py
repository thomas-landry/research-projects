"""
Tests for FuzzyDeduplicator and its integration into ContentFilter.
"""
import pytest
from core.fuzzy_deduplicator import FuzzyDeduplicator
from core.content_filter import ContentFilter
from core.parser import DocumentChunk

class TestFuzzyDeduplicator:
    def test_deduplicate_exact_duplicates(self):
        deduper = FuzzyDeduplicator()
        chunks = ["Hello World", "Hello World", "Unique"]
        result = deduper.deduplicate(chunks)
        assert len(result) == 2
        assert result == ["Hello World", "Unique"]
        
    def test_deduplicate_fuzzy_duplicates(self):
        deduper = FuzzyDeduplicator(similarity_threshold=0.9)
        # "Hello World" vs "Hello World!" (very similar)
        chunks = ["Hello World", "Hello World!", "Distinct Content"]
        result = deduper.deduplicate(chunks)
        assert len(result) == 2
        assert "Distinct Content" in result
        # Should keep the first occurrence usually
        assert result[0] == "Hello World"

    def test_deduplicate_with_indices(self):
        deduper = FuzzyDeduplicator(similarity_threshold=0.9)
        chunks = ["A", "A", "B"]
        result, indices = deduper.deduplicate_with_indices(chunks)
        assert result == ["A", "B"]
        assert indices == [0, 2]

class TestContentFilterIntegration:
    def test_filter_chunks_deduplicates(self):
        """Test that content filter removes duplicates when enabled."""
        
        # We need to make sure ContentFilter uses Deduplicator.
        # Assuming we check 'deduplicate=True' default or similar.
        
        filter = ContentFilter() 
        # Manually enable checking if we add a flag, or assume it's on.
        # For TDD, we expect it to be on or addable.
        
        chunks = [
            DocumentChunk(text="Repeated Content", section="Intro", source_file="doc1"),
            DocumentChunk(text="Repeated Content", section="Intro", source_file="doc1"),
            DocumentChunk(text="Unique Content", section="Methods", source_file="doc1")
        ]
        
        result = filter.filter_chunks(chunks)
        
        # Should filter out the second "Repeated Content"
        assert len(result.filtered_chunks) == 2
        assert result.filtered_chunks[0].text == "Repeated Content"
        assert result.filtered_chunks[1].text == "Unique Content"
        
        # Check stats
        assert result.token_stats["removed_chunks"] >= 1

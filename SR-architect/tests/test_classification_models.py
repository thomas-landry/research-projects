"""
Tests for classification models.

TDD RED PHASE: These tests will FAIL because core/classification/models.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from pydantic import ValidationError
from core.classification.models import (
    RelevanceResult,
    ChunkRelevance,
    RelevanceResponse,
    coerce_relevance_list
)


class TestRelevanceResult:
    """Test RelevanceResult dataclass."""
    
    def test_relevance_result_creation_minimal(self):
        """Should create RelevanceResult with all required fields."""
        result = RelevanceResult(
            chunk_index=0,
            is_relevant=True,
            confidence=0.95,
            reason="Contains patient demographics"
        )
        assert result.chunk_index == 0
        assert result.is_relevant is True
        assert result.confidence == 0.95
        assert result.reason == "Contains patient demographics"
    
    def test_relevance_result_not_relevant(self):
        """Should create RelevanceResult for irrelevant chunk."""
        result = RelevanceResult(
            chunk_index=5,
            is_relevant=False,
            confidence=0.5,
            reason="References section"
        )
        assert result.is_relevant is False
        assert result.chunk_index == 5


class TestChunkRelevance:
    """Test ChunkRelevance Pydantic model."""
    
    def test_chunk_relevance_creation_relevant(self):
        """Should create ChunkRelevance for relevant chunk."""
        chunk = ChunkRelevance(
            index=0,
            relevant=1,
            reason="Contains extraction fields"
        )
        assert chunk.index == 0
        assert chunk.relevant == 1
        assert chunk.reason == "Contains extraction fields"
    
    def test_chunk_relevance_creation_irrelevant(self):
        """Should create ChunkRelevance for irrelevant chunk."""
        chunk = ChunkRelevance(
            index=2,
            relevant=0,
            reason="Background information only"
        )
        assert chunk.index == 2
        assert chunk.relevant == 0
    
    def test_relevant_field_validation_valid(self):
        """Should accept 0 and 1 for relevant field."""
        # Valid: 0
        chunk0 = ChunkRelevance(index=0, relevant=0, reason="test")
        assert chunk0.relevant == 0
        
        # Valid: 1
        chunk1 = ChunkRelevance(index=0, relevant=1, reason="test")
        assert chunk1.relevant == 1
    
    def test_relevant_field_validation_invalid(self):
        """Should reject values outside [0, 1] range."""
        # Invalid: 2
        with pytest.raises(ValidationError):
            ChunkRelevance(index=0, relevant=2, reason="test")
        
        # Invalid: -1
        with pytest.raises(ValidationError):
            ChunkRelevance(index=0, relevant=-1, reason="test")


class TestCoerceRelevanceList:
    """Test coerce_relevance_list helper function."""
    
    def test_coerce_simple_int_list(self):
        """Should coerce [0, 1, 0] to ChunkRelevance dicts."""
        result = coerce_relevance_list([0, 1, 0])
        
        assert len(result) == 3
        assert result[0]["index"] == 0
        assert result[0]["relevant"] == 0
        assert "reason" in result[0]
        
        assert result[1]["index"] == 1
        assert result[1]["relevant"] == 1
        
        assert result[2]["index"] == 2
        assert result[2]["relevant"] == 0
    
    def test_coerce_string_list(self):
        """Should coerce ['0', '1', '0'] to ChunkRelevance dicts."""
        result = coerce_relevance_list(["0", "1", "0"])
        
        assert len(result) == 3
        assert result[0]["relevant"] == 0
        assert result[1]["relevant"] == 1
        assert result[2]["relevant"] == 0
    
    def test_coerce_mixed_truthy_values(self):
        """Should coerce various truthy values to 1."""
        result = coerce_relevance_list(["1", "true", "yes", "True", "YES"])
        
        for item in result:
            assert item["relevant"] == 1
    
    def test_coerce_mixed_falsy_values(self):
        """Should coerce various falsy values to 0."""
        result = coerce_relevance_list(["0", "false", "no", "False", "NO"])
        
        for item in result:
            assert item["relevant"] == 0
    
    def test_coerce_already_dict_list(self):
        """Should pass through already-formatted dict list."""
        input_list = [
            {"index": 0, "relevant": 1, "reason": "test"},
            {"index": 1, "relevant": 0, "reason": "test2"}
        ]
        result = coerce_relevance_list(input_list)
        
        # Should return unchanged
        assert result == input_list
    
    def test_coerce_empty_list(self):
        """Should handle empty list."""
        result = coerce_relevance_list([])
        assert result == []


class TestRelevanceResponse:
    """Test RelevanceResponse Pydantic model."""
    
    def test_relevance_response_creation(self):
        """Should create RelevanceResponse with classifications."""
        classifications = [
            ChunkRelevance(index=0, relevant=1, reason="Contains data"),
            ChunkRelevance(index=1, relevant=0, reason="Background")
        ]
        
        response = RelevanceResponse(classifications=classifications)
        
        assert len(response.classifications) == 2
        assert response.classifications[0].index == 0
        assert response.classifications[0].relevant == 1
    
    def test_relevance_response_with_coercion(self):
        """Should coerce simple list through BeforeValidator."""
        # This should trigger _coerce_relevance_list
        response = RelevanceResponse(classifications=[0, 1, 0])
        
        assert len(response.classifications) == 3
        assert response.classifications[0].relevant == 0
        assert response.classifications[1].relevant == 1
        assert response.classifications[2].relevant == 0
    
    def test_relevance_response_empty(self):
        """Should handle empty classifications."""
        response = RelevanceResponse(classifications=[])
        assert len(response.classifications) == 0

"""
Tests for SchemaDiscoveryAgent.

These tests verify the schema discovery and unification logic.
"""
import pytest
from unittest.mock import MagicMock, patch
from agents.schema_discovery import SchemaDiscoveryAgent, SuggestedField, UnifiedField, UnificationResult, DiscoveryResult


def _create_mock_completion():
    """Helper to create mock completion objects."""
    mock_completion = MagicMock()
    mock_completion.usage = MagicMock()
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50
    mock_completion.usage.total_tokens = 150
    return mock_completion


def test_unify_fields_logic():
    """Test that unify_fields correctly merges synonymous fields."""
    mock_unified_result = UnificationResult(fields=[
        UnifiedField(
            canonical_name="patient_age",
            description="Age of patient",
            field_type="integer",
            synonyms_merged=["age", "patient_age_years"],
            frequency=2
        )
    ])
    
    mock_completion = _create_mock_completion()
    mock_client = MagicMock()
    # Return tuple (result, completion) as instructor does
    mock_client.chat.completions.create_with_completion.return_value = (mock_unified_result, mock_completion)
    
    agent = SchemaDiscoveryAgent()
    agent._client = mock_client  # Inject mock client
    
    raw_suggestions = [
        SuggestedField(field_name="age", description="Age", data_type="int", example_value="55", extraction_difficulty="easy", section_found="Results"),
        SuggestedField(field_name="patient_age_years", description="Age in years", data_type="integer", example_value="55", extraction_difficulty="easy", section_found="Methods")
    ]
    
    unified = agent.unify_fields(raw_suggestions)
    
    assert len(unified) == 1
    assert unified[0].canonical_name == "patient_age"
    assert "age" in unified[0].synonyms_merged
    assert unified[0].frequency == 2


def test_unify_fields_empty():
    """Test that empty input returns empty list."""
    agent = SchemaDiscoveryAgent()
    assert agent.unify_fields([]) == []


def test_unify_fallback_on_error():
    """Test that unification falls back to 1-to-1 mapping on error."""
    mock_client = MagicMock()
    mock_client.chat.completions.create_with_completion.side_effect = Exception("LLM Error")
    
    agent = SchemaDiscoveryAgent()
    agent._client = mock_client  # Inject mock client
    
    raw = [SuggestedField(field_name="foo", description="bar", data_type="text", example_value="baz", extraction_difficulty="easy", section_found="everywhere")]
    
    unified = agent.unify_fields(raw)
    
    # Should fallback to 1-to-1 mapping
    assert len(unified) == 1
    assert unified[0].canonical_name == "foo"
    assert unified[0].frequency == 1

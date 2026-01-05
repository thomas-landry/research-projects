import pytest
from unittest.mock import MagicMock, patch
from agents.schema_discovery import SchemaDiscoveryAgent, SuggestedField, UnifiedField, UnificationResult, DiscoveryResult

@pytest.fixture
def mock_utils():
    with patch("core.utils.get_llm_client") as mock:
        yield mock

def test_unify_fields_logic(mock_utils):
    # Setup mock LLM response
    mock_unified_result = UnificationResult(fields=[
        UnifiedField(
            canonical_name="patient_age",
            description="Age of patient",
            field_type="integer",
            synonyms_merged=["age", "patient_age_years"],
            frequency=2
        )
    ])
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_unified_result
    mock_utils.return_value = mock_client
    
    agent = SchemaDiscoveryAgent()
    
    raw_suggestions = [
        SuggestedField(field_name="age", description="Age", data_type="int", example_value="55", extraction_difficulty="easy", section_found="Results"),
        SuggestedField(field_name="patient_age_years", description="Age in years", data_type="integer", example_value="55", extraction_difficulty="easy", section_found="Methods")
    ]
    
    unified = agent.unify_fields(raw_suggestions)
    
    assert len(unified) == 1
    assert unified[0].canonical_name == "patient_age"
    assert "age" in unified[0].synonyms_merged
    assert unified[0].frequency == 2

def test_unify_fields_empty(mock_utils):
    agent = SchemaDiscoveryAgent()
    assert agent.unify_fields([]) == []

def test_unify_fallback_on_error(mock_utils):
    # Setup mock to raise error
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("LLM Error")
    mock_utils.return_value = mock_client
    
    agent = SchemaDiscoveryAgent()
    raw = [SuggestedField(field_name="foo", description="bar", data_type="text", example_value="baz", extraction_difficulty="easy", section_found="everywhere")]
    
    unified = agent.unify_fields(raw)
    
    # Should fallback to 1-to-1 mapping
    assert len(unified) == 1
    assert unified[0].canonical_name == "foo"
    assert unified[0].frequency == 1

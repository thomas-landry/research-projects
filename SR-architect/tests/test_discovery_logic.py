
import pytest
from unittest.mock import MagicMock, patch
from agents.schema_discovery import SchemaDiscoveryAgent, SuggestedField, UnifiedField, DiscoveryResult
from core.schema_builder import FieldDefinition, FieldType

def test_discover_schema_with_existing_fields():
    agent = SchemaDiscoveryAgent()
    
    # Mock get_sample_papers
    agent.get_sample_papers = MagicMock(return_value=["paper1.pdf"])
    
    # Mock analyze_paper
    mock_discovery_result = DiscoveryResult(
        filename="paper1.pdf",
        suggested_fields=[
            SuggestedField(
                field_name="new_field", 
                description="A new field", 
                data_type="text", 
                example_value="val", 
                extraction_difficulty="easy", 
                section_found="Results"
            ),
            SuggestedField(
                field_name="existing_field", 
                description="Should be ignored", 
                data_type="text", 
                example_value="val", 
                extraction_difficulty="easy", 
                section_found="Results"
            )
        ],
        paper_type="case_report"
    )
    agent.analyze_paper = MagicMock(return_value=mock_discovery_result)
    
    # Mock unify_fields
    mock_unified = [
        UnifiedField(
            canonical_name="new_field",
            description="A new field",
            field_type="text",
            synonyms_merged=["new_field"],
            frequency=1
        ),
        UnifiedField(
            canonical_name="existing_field",
            description="Should be ignored",
            field_type="text",
            synonyms_merged=["existing_field"],
            frequency=1
        )
    ]
    agent.unify_fields = MagicMock(return_value=mock_unified)
    
    existing_schema = [
        FieldDefinition(name="existing_field", description="Already here")
    ]
    
    # Run discovery
    results = agent.discover_schema("dummy_dir", sample_size=1, existing_schema=existing_schema)
    
    # Verify results
    assert len(results) == 1
    assert results[0].name == "new_field"
    
    # Verify analyze_paper was called with existing_fields
    agent.analyze_paper.assert_called_with("paper1.pdf", existing_fields=["existing_field"])

if __name__ == "__main__":
    pytest.main([__file__])

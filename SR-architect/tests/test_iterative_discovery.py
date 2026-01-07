
import pytest
from unittest.mock import MagicMock
from agents.schema_discovery import SchemaDiscoveryAgent, SuggestedField, UnifiedField, DiscoveryResult

def test_iterative_discovery_accumulates_fields():
    agent = SchemaDiscoveryAgent()
    
    # Mock sampling to return 3 papers
    agent.get_sample_papers = MagicMock(return_value=["p1.pdf", "p2.pdf", "p3.pdf"])
    
    # Mock analyze_paper to simulate finding NEW things based on what's known
    def analyze_side_effect(paper_path, existing_fields=None):
        existing = existing_fields or []
        suggestions = []
        
        # Paper 1 finds "Field_A"
        if paper_path == "p1.pdf":
            suggestions.append(SuggestedField(field_name="field_a", description="A", data_type="text", example_value="a", extraction_difficulty="easy", section_found="S1"))
            
        # Paper 2 finds "Field_B" only if "Field_A" is already known (simulating deep dig)
        elif paper_path == "p2.pdf":
            if "field_a" in existing:
                suggestions.append(SuggestedField(field_name="field_b", description="B", data_type="text", example_value="b", extraction_difficulty="easy", section_found="S1"))
            else:
                # If we didn't know A, we'd probably just find A again
                suggestions.append(SuggestedField(field_name="field_a", description="A", data_type="text", example_value="a", extraction_difficulty="easy", section_found="S1"))
                
        # Paper 3 finds "Field_C" only if A and B are known
        elif paper_path == "p3.pdf":
            if "field_a" in existing and "field_b" in existing:
                suggestions.append(SuggestedField(field_name="field_c", description="C", data_type="text", example_value="c", extraction_difficulty="easy", section_found="S1"))
            else:
                suggestions.append(SuggestedField(field_name="field_a", description="A", data_type="text", example_value="a", extraction_difficulty="easy", section_found="S1"))
                
        return DiscoveryResult(filename=paper_path, suggested_fields=suggestions, paper_type="test")

    agent.analyze_paper = MagicMock(side_effect=analyze_side_effect)
    
    # Mock unification to just pass through whatever we found
    def unify_side_effect(suggestions):
        return [
            UnifiedField(canonical_name=s.field_name, description=s.description, field_type=s.data_type, synonyms_merged=[s.field_name], frequency=1)
            for s in suggestions
        ]
    agent.unify_fields = MagicMock(side_effect=unify_side_effect)
    
    # Run discovery
    results = agent.discover_schema("dummy_dir", sample_size=3)
    
    # We expect A, B, and C
    found_names = [f.name for f in results]
    assert "field_a" in found_names
    assert "field_b" in found_names
    assert "field_c" in found_names
    
    # Verify analyze_paper calls grew the existing_fields list
    # Call 1: existing=None (or [])
    # Call 2: existing=['field_a']
    # Call 3: existing=['field_a', 'field_b']
    
    # We can inspect call args
    calls = agent.analyze_paper.call_args_list
    assert len(calls) == 3
    
    # Check Call 2 args
    args, kwargs = calls[1]
    assert "field_a" in kwargs['existing_fields']
    
    # Check Call 3 args
    args, kwargs = calls[2]
    assert "field_a" in kwargs['existing_fields']
    assert "field_b" in kwargs['existing_fields']

if __name__ == "__main__":
    pytest.main([__file__])

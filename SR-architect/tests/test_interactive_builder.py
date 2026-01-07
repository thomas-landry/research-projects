
import pytest
from unittest.mock import patch, MagicMock
from core.schema_builder import interactive_schema_builder, FieldDefinition

def test_interactive_builder_undo():
    # We want to simulate:
    # 1. Add field 'a'
    # 2. Add field 'b'
    # 3. Type 'undo'
    # 4. Press Enter (finish)
    # Result should only contain 'a'.
    
    with patch("rich.prompt.Prompt.ask") as mock_ask, \
         patch("rich.prompt.Confirm.ask") as mock_confirm:
        
        # Setup sequence of answers
        mock_ask.side_effect = [
            "custom", # Use predefined?
            "field_a", "desc a", "text", # Field 1
            "field_b", "desc b", "text", # Field 2
            "undo", # UNDO
            "" # Finish
        ]
        mock_confirm.side_effect = [True, True, True, True] # Required, Quote for A and B
        
        fields = interactive_schema_builder()
        
        assert len(fields) == 1
        assert fields[0].name == "field_a"

def test_interactive_builder_delete():
    # Simulate:
    # 1. Add 'field_a'
    # 2. Add 'field_b'
    # 3. Type 'delete field_a'
    # 4. Finish
    # Result: only 'field_b'
    
    with patch("rich.prompt.Prompt.ask") as mock_ask, \
         patch("rich.prompt.Confirm.ask") as mock_confirm:
        
        mock_ask.side_effect = [
            "custom",
            "field_a", "desc a", "text",
            "field_b", "desc b", "text",
            "delete field_a",
            ""
        ]
        mock_confirm.side_effect = [True, True, True, True]
        
        fields = interactive_schema_builder()
        
        assert len(fields) == 1
        assert fields[0].name == "field_b"

def test_interactive_discovery_undo():
    from agents.schema_discovery import interactive_discovery
    
    with patch("rich.prompt.Prompt.ask") as mock_ask, \
         patch("rich.prompt.Confirm.ask") as mock_confirm, \
         patch("agents.schema_discovery.SchemaDiscoveryAgent.discover_schema") as mock_discover:
        
        # Mock discovery to return empty initially
        mock_discover.return_value = []
        
        # 1. Start discovery (empty)
        # 2. Add custom fields? Yes
        # 3. Field 1
        # 4. Undo
        # 5. Finish
        mock_confirm.side_effect = [True, True] # Add custom fields?, Finish? (Wait, confirm loop is different)
        # Sequence:
        # interactive_discovery calls agent.discover_schema -> returns []
        # Prints "No new fields discovered"
        # returns [] (Wait, the logic returns early if no suggestions)
        
        # Let's mock it finding something
        mock_discover.return_value = [FieldDefinition(name="discovered_1", description="desc")]
        
        mock_ask.side_effect = [
            "manual_1", "desc manual",
            "undo",
            ""
        ]
        mock_confirm.side_effect = [
            True, # Include 'discovered_1'?
            True, # Add more custom fields manually?
        ]
        
        fields = interactive_discovery("dummy_dir")
        
        # Should have 'discovered_1' but NOT 'manual_1'
        assert len(fields) == 1
        assert fields[0].name == "discovered_1"


import pytest
from unittest.mock import MagicMock
from typing import List
from core.schema_builder import FieldDefinition

def test_discovery_agent_interface():
    # Attempt to import the base interface
    try:
        from agents.discovery import DiscoveryAgent
    except ImportError:
        pytest.fail("Could not import DiscoveryAgent from agents.discovery")

    # Verify it is a Protocol or ABC
    class ConcreteDiscovery(DiscoveryAgent):
        def discover_schema(self, papers_dir: str, sample_size: int = 3) -> List[FieldDefinition]:
            return []

    agent = ConcreteDiscovery()
    assert hasattr(agent, "discover_schema")

def test_schema_discovery_agent_implements_interface():
    try:
        from agents.schema_discovery import SchemaDiscoveryAgent
        from agents.discovery import DiscoveryAgent
    except ImportError:
        pytest.fail("Could not import agents")
        
    # Verify SchemaDiscoveryAgent follows the protocol
    assert issubclass(SchemaDiscoveryAgent, DiscoveryAgent)


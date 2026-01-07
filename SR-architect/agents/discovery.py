from typing import List, Protocol, runtime_checkable, Dict, Optional
from core.schema_builder import FieldDefinition

@runtime_checkable
class DiscoveryAgent(Protocol):
    """
    Interface for agents that discover schema fields from content.
    """
    
    def discover_schema(self, papers_dir: str, sample_size: int = 3) -> List[FieldDefinition]:
        """
        Analyze a sample of papers to discover potential extraction fields.
        
        Args:
            papers_dir: Directory containing PDFs
            sample_size: Number of papers to analyze
            
        Returns:
            List of suggested FieldDefinition objects
        """
        ...

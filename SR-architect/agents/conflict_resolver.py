#!/usr/bin/env python3
"""
Conflict Resolver Agent - Resolves discrepancies between different parts of a paper.

This agent is called when multiple values are found for the same field (e.g. Abstract says N=50, Table says N=48).
It uses hierarchical logic (Consort Flow Diagram > Table > Results > Abstract) to decide.
"""

import sys
from pathlib import Path
from typing import List, Any, Optional
from pydantic import BaseModel, Field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class ResolvedValue(BaseModel):
    """The final resolved value after conflict analysis."""
    value: Any = Field(description="The chosen correct value")
    confidence: float = Field(description="Confidence in this choice (0-1)")
    reasoning: str = Field(description="Why this value was chosen over others")
    source_section: str = Field(description="Which section provided the winning value")

class ConflictResolverAgent:
    """
    Resolves discrepancies in extracted data.
    """
    
    RESOLVER_PROMPT = """You are a conflict resolution judge for scientific data extraction.
    
    You have found MULTIPLE values for the field '{field_name}'.
    You must decide which one is correct.
    
    CANDIDATES:
    {candidates_str}
    
    RULES OF PRECEDENCE:
    1. CONSORT Flow Diagrams (most accurate for sample sizes)
    2. Tables (usually more precise than text)
    3. Results Section (more detailed than Abstract)
    4. Abstract (often rounded or simplified)
    
    Analyze the context and choose the most likely correct value.
    If they are measuring slightly different things (e.g. "randomized" vs "analyzed"), 
    choose the one matching this definition: {field_desc}
    """
    
    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or "gpt-4o" # Needs high logic capabilities
        self._client = None
        
        from core.utils import get_logger
        self.logger = get_logger("ConflictResolverAgent")
        
    @property
    def client(self):
        if self._client is not None:
            return self._client
        from core.utils import get_llm_client
        self._client = get_llm_client(self.provider)
        return self._client

    def resolve(self, field_name: str, field_desc: str, values: List[Any], sources: List[str]) -> ResolvedValue:
        """
        Resolve conflict between multiple values.
        
        Args:
            field_name: Name of the field (e.g., 'sample_size')
            field_desc: Description of what we are looking for
            values: List of conflicting values found
            sources: List of sections where they were found (same order)
        """
        if not values:
            return ResolvedValue(value=None, confidence=0.0, reasoning="No values provided", source_section="None")
            
        if len(set(str(v) for v in values)) == 1:
            # All same
            return ResolvedValue(
                value=values[0], 
                confidence=1.0, 
                reasoning="All sources agree.", 
                source_section=sources[0]
            )
            
        # Prepare candidates string
        candidates = []
        for v, s in zip(values, sources):
            candidates.append(f"- Value: {v} | Source: {s}")
        candidates_str = "\n".join(candidates)
        
        prompt = self.RESOLVER_PROMPT.format(
            field_name=field_name,
            field_desc=field_desc,
            candidates_str=candidates_str
        )
        
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=ResolvedValue,
            )
            return result
        except Exception as e:
            self.logger.error(f"Failed to resolve conflict: {e}")
            # Fallback: take the first one (naive)
            return ResolvedValue(
                value=values[0],
                confidence=0.5,
                reasoning=f"Resolution failed ({e}), default to first.",
                source_section=sources[0]
            )

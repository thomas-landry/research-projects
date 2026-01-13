#!/usr/bin/env python3
"""
Classification models for relevance classification.

Contains Pydantic models and dataclasses for chunk relevance classification.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Annotated
from pydantic import BaseModel, Field, BeforeValidator


@dataclass
class RelevanceResult:
    """Result for a single chunk's relevance classification."""
    chunk_index: int
    is_relevant: bool
    confidence: float
    reason: str


class ChunkRelevance(BaseModel):
    """Pydantic model for structured relevance output."""
    index: int
    relevant: int = Field(ge=0, le=1)  # 0 or 1
    reason: str


def coerce_relevance_list(v: Any) -> List[Dict[str, Any]]:
    """
    Coerce simplified LLM output (list of strings/ints) into ChunkRelevance objects.
    Handle: ["0", "1", "0"] -> [{"index": 0, "relevant": 0, "reason": "inferred"}, ...]
    """
    if isinstance(v, list) and v:
        # Check if it's a list of primitives (str or int)
        if isinstance(v[0], (str, int)) and not isinstance(v[0], dict):
            coerced = []
            for i, val in enumerate(v):
                # Clean value
                val_str = str(val).strip().lower()
                is_relevant = 1 if val_str in ('1', 'true', 'yes') else 0
                
                coerced.append({
                    "index": i,
                    "relevant": is_relevant,
                    "reason": "Inferred from simplified output"
                })
            return coerced
    return v


class RelevanceResponse(BaseModel):
    """Batch response for relevance classification."""
    classifications: Annotated[List[ChunkRelevance], BeforeValidator(coerce_relevance_list)]

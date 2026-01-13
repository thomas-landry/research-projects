#!/usr/bin/env python3
"""
Extractor models for evidence-based extraction.

Contains Pydantic models for evidence items and extraction results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    """Citation evidence for a single extracted value."""
    field_name: str = Field(description="Name of the extracted field")
    extracted_value: Any = Field(description="The value that was extracted")
    exact_quote: Optional[str] = Field(default="", description="Verbatim quote from source text supporting this value")
    page_number: Optional[int] = Field(default=None, description="Page number if known")
    chunk_index: Optional[int] = Field(default=None, description="Index of source chunk")
    start_char: Optional[int] = Field(default=None, description="Start character index in source")
    end_char: Optional[int] = Field(default=None, description="End character index in source")
    confidence: float = Field(ge=0.0, le=1.0, default=0.9, description="Confidence in extraction accuracy")
    
    @field_validator('exact_quote', mode='before')
    @classmethod
    def coerce_quote_to_string(cls, value) -> str:
        """Coerce None to empty string for robustness with local LLMs."""
        if value is None:
            return ""
        return str(value)


class ExtractionWithEvidence(BaseModel):
    """Wrapper combining extracted data with provenance evidence."""
    data: Dict[str, Any] = Field(description="The extracted field values")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Evidence citations for each value")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    """Response model for evidence extraction."""
    evidence: List[EvidenceItem]

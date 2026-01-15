#!/usr/bin/env python3
"""
Validation models for extraction checking.

Contains Pydantic models and dataclasses used by ExtractionChecker.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator


class Issue(BaseModel):
    """A specific issue found during validation."""
    field: str
    issue_type: str  # "mismatch", "missing_quote", "semantic_error", "inconsistent"
    severity: str = "medium"  # "low", "medium", "high"
    detail: str
    suggested_fix: Optional[str] = None
    
    @field_validator('issue_type', 'field', 'detail', mode='before')
    @classmethod
    def coerce_to_string(_, value) -> str:
        """Handle local LLMs returning lists or other types instead of strings."""
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        if value is None:
            return ""
        return str(value)


class CheckerResponse(BaseModel):
    """Structured response from the checker LLM."""
    accuracy_score: float = Field(ge=0.0, le=1.0, description="Do values match their cited quotes?")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Do semantics align with theme?")
    issues: List[Issue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list, description="Revision prompts for extractor")
    
    @field_validator('accuracy_score', 'consistency_score', mode='before')
    @classmethod
    def coerce_score_to_float(_, value) -> float:
        """Handle local LLMs returning None or invalid score values."""
        if value is None:
            return 0.0
        try:
            score = float(value)
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except (ValueError, TypeError):
            return 0.0
    
    @field_validator('suggestions', mode='before')
    @classmethod
    def coerce_suggestions_to_strings(_, value) -> List[str]:
        """Handle local LLMs returning dicts like {'text': '...'} instead of strings."""
        if not value:
            return []
        result = []
        for suggestion_item in value:
            if isinstance(suggestion_item, dict):
                # Extract text from dict format
                result.append(suggestion_item.get('text', suggestion_item.get('suggestion', str(suggestion_item))))
            elif isinstance(suggestion_item, str):
                result.append(suggestion_item)
            else:
                result.append(str(suggestion_item))
        return result


@dataclass
class CheckerResult:
    """Result of extraction validation."""
    accuracy_score: float
    consistency_score: float
    overall_score: float
    issues: List[Issue]
    suggestions: List[str]
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy_score": self.accuracy_score,
            "consistency_score": self.consistency_score,
            "overall_score": self.overall_score,
            "issues": [i.model_dump() for i in self.issues],
            "suggestions": self.suggestions,
            "passed": self.passed,
        }

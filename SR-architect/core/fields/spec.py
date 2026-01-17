"""
ColumnSpec - Machine-readable column specification.

Defines metadata for schema fields including extraction policies,
validation rules, and prompt generation.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Type
from pydantic import Field
from pydantic.fields import FieldInfo

from core.types.enums import ExtractionPolicy


@dataclass
class ColumnSpec:
    """Machine-readable column specification."""
    key: str
    dtype: Type  # FindingReport, MeasurementData, str, int, etc.
    description: str
    extraction_policy: ExtractionPolicy
    source_narrative_field: Optional[str] = None
    high_confidence_keywords: Optional[List[str]] = None
    requires_evidence_quote: bool = False
    validation: Optional[Dict[str, Any]] = None
    
    def to_field(self) -> FieldInfo:
        """Convert ColumnSpec to Pydantic Field."""
        # Create serializable spec dict
        spec_dict = asdict(self)
        
        # Convert Type objects to string names for JSON serialization
        if isinstance(self.dtype, type):
            spec_dict['dtype'] = self.dtype.__name__
        else:
            spec_dict['dtype'] = str(self.dtype)

        return Field(
            default=None,
            description=self.description,
            json_schema_extra={"column_spec": spec_dict},
        )


def generate_extraction_prompt(spec: ColumnSpec, narrative: str) -> str:
    """Generate LLM extraction prompt from ColumnSpec."""
    
    policy_instructions = {
        ExtractionPolicy.MUST_BE_EXPLICIT: (
            "CRITICAL: This information MUST be explicitly stated in the text. "
            "Do not infer or assume. Only extract if clearly mentioned."
        ),
        ExtractionPolicy.CAN_BE_INFERRED: (
            "You may infer this from context if not explicitly stated."
        ),
        ExtractionPolicy.METADATA: (
            "Extract directly from document metadata or header."
        ),
        ExtractionPolicy.DERIVED: (
            "This field is derived from other fields. Do not extract directly."
        ),
        ExtractionPolicy.HUMAN_REVIEW: (
            "This field requires human review. Extract with evidence quote."
        ),
    }
    
    keywords_hint = ""
    if spec.high_confidence_keywords:
        keywords_hint = f"\n\nLook for keywords: {', '.join(spec.high_confidence_keywords)}"
    
    evidence_requirement = ""
    if spec.requires_evidence_quote:
        evidence_requirement = "\n\nProvide an exact quote from the text as evidence."
    
    prompt = f"""
Extract: {spec.description}

Extraction Policy: {policy_instructions[spec.extraction_policy]}{keywords_hint}{evidence_requirement}

Text:
{narrative}

Return the extracted value or null if not found.
""".strip()
    
    return prompt

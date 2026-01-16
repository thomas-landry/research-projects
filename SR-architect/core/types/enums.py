"""
Core type enums for semantic schema.

Defines tri-state Status, AggregationUnit, and ExtractionPolicy enums
for binary data extraction with frequencies.
"""

from enum import Enum


class Status(str, Enum):
    """Tri-state for explicitly reported outcomes."""
    PRESENT = "present"
    ABSENT = "absent"
    NOT_REPORTED = "not_reported"
    UNCLEAR = "unclear"


class AggregationUnit(str, Enum):
    """Level at which finding is reported."""
    PATIENT = "patient"
    LESION = "lesion"
    SPECIMEN = "specimen"
    BIOPSY = "biopsy"
    IMAGING_SERIES = "imaging_series"
    UNCLEAR = "unclear"


class ExtractionPolicy(str, Enum):
    """How to extract this field."""
    METADATA = "metadata"           # Always extracted (title, authors)
    CAN_BE_INFERRED = "inferred"    # LLM can infer from context
    MUST_BE_EXPLICIT = "explicit"   # Requires explicit statement
    DERIVED = "derived"             # Rule-based from other fields
    HUMAN_REVIEW = "human_review"   # Always flag for review

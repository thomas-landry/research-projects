"""
Core type models for semantic schema.

Defines FindingReport, MeasurementData, and CountData Pydantic models
for structured data extraction with validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from core.types.enums import Status, AggregationUnit


class FindingReport(BaseModel):
    """Standard format for any binary finding with frequencies."""
    status: Optional[Status] = None
    n: Optional[int] = Field(None, ge=0, description="Count with finding")
    N: Optional[int] = Field(None, ge=0, description="Total assessed")
    aggregation_unit: AggregationUnit = AggregationUnit.PATIENT
    aggregation_note: Optional[str] = None
    evidence_quote: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @model_validator(mode='after')
    def validate_n_not_exceed_N(self):
        """Validate that n does not exceed N."""
        if self.n is not None and self.N is not None:
            if self.n > self.N:
                raise ValueError(f"Numerator ({self.n}) cannot exceed denominator ({self.N})")
        return self


class MeasurementData(BaseModel):
    """Generic continuous measurement with normalization."""
    raw_text: Optional[str] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_point_estimate: Optional[float] = None
    value_unit: Optional[str] = None  # "years", "months", "mm"
    value_type: Optional[str] = None  # "mean", "median", "range"


class CountData(BaseModel):
    """Structured count with context."""
    raw_text: Optional[str] = None
    count_value: Optional[int] = Field(None, ge=0)
    count_unit: Optional[str] = None  # "patients", "lesions"

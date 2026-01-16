"""
DPMCohort Schema - Cohort-level extraction for DPM systematic review.

One row per cohort, not per paper. Enables stratified analysis and
coherent denominators for meta-analysis.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from core.types.models import FindingReport, MeasurementData
from core.types.enums import AggregationUnit
from core.fields.library import FieldLibrary as FL


class DPMCohort(BaseModel):
    """
    Cohort-level extraction for DPM systematic review.
    
    One row per cohort, not per paper.
    Enables stratified analysis and coherent denominators.
    """
    
    # =========================================================================
    # STUDY LINKAGE
    # =========================================================================
    study_id: str = Field(..., description="Unique study identifier (FirstAuthor_Year)")
    cohort_id: str = Field(..., description="Unique cohort identifier (Smith_2020_stageI)")
    cohort_label: Optional[str] = Field(None, description="Label for cohort (e.g., 'Stage I patients')")
    cohort_n_patients: int = Field(..., ge=1, description="Number of patients in THIS cohort")
    
    # =========================================================================
    # STUDY METADATA (duplicated across cohorts from same study)
    # =========================================================================
    title: Optional[str] = FL.TITLE.to_field()
    authors: Optional[str] = FL.AUTHORS.to_field()
    doi: Optional[str] = FL.DOI.to_field()
    year: Optional[int] = FL.YEAR.to_field()
    study_type: Optional[str] = FL.STUDY_TYPE.to_field()
    
    # =========================================================================
    # DEMOGRAPHICS (structured with normalization)
    # =========================================================================
    age: Optional[MeasurementData] = FL.AGE.to_field()
    sex_female: Optional[FindingReport] = FL.SEX_FEMALE.to_field()
    
    # =========================================================================
    # CT FINDINGS (tri-state + n/N)
    # =========================================================================
    ct_ground_glass: Optional[FindingReport] = FL.imaging_finding(
        "ground_glass",
        ["GGO", "ground glass", "ground-glass"]
    ).to_field()
    
    ct_solid_nodules: Optional[FindingReport] = FL.imaging_finding(
        "solid_nodules",
        ["solid nodule", "solid lesion"]
    ).to_field()
    
    ct_central_cavitation: Optional[FindingReport] = FL.imaging_finding(
        "central_cavitation",
        ["cavitation", "cavitary"]
    ).to_field()
    
    # =========================================================================
    # NARRATIVES (for rule derivation)
    # =========================================================================
    ct_narrative: Optional[str] = Field(
        None,
        description="Full narrative of CT findings"
    )
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @model_validator(mode='after')
    def validate_patient_denominators(self):
        """
        Validate that patient-level findings don't exceed cohort size.
        
        For findings with aggregation_unit=PATIENT, N should not exceed
        cohort_n_patients.
        """
        patient_level_fields = [
            'ct_ground_glass',
            'ct_solid_nodules',
            'ct_central_cavitation',
            'sex_female',
        ]
        
        for field_name in patient_level_fields:
            finding = getattr(self, field_name, None)
            if finding is None:
                continue
            
            if not isinstance(finding, FindingReport):
                continue
            
            # Only validate patient-level findings
            if finding.aggregation_unit != AggregationUnit.PATIENT:
                continue
            
            # Check denominator doesn't exceed cohort size
            if finding.N is not None and finding.N > self.cohort_n_patients:
                raise ValueError(
                    f"{field_name}: Patient-level denominator ({finding.N}) "
                    f"exceeds cohort size ({self.cohort_n_patients})"
                )
        
        return self

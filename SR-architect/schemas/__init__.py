"""SR-Architect schemas module."""

from schemas.dpm_modular import (
    StudyMetadataSchema,
    DemographicsSchema,
    SymptomsSchema,
    AssociatedConditionsSchema,
    ImagingSchema,
    PathologySchema,
    ImmunohistochemistrySchema,
    DiagnosticApproachSchema,
    OutcomesSchema,
    DPMFullExtractionSchema,
    IndividualPatientData,
    AggregateStudyData,
)

__all__ = [
    "StudyMetadataSchema",
    "DemographicsSchema",
    "SymptomsSchema",
    "AssociatedConditionsSchema",
    "ImagingSchema",
    "PathologySchema",
    "ImmunohistochemistrySchema",
    "DiagnosticApproachSchema",
    "OutcomesSchema",
    "DPMFullExtractionSchema",
    "IndividualPatientData",
    "AggregateStudyData",
]

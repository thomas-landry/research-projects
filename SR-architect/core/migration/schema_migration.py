"""
Schema Migration - Convert legacy data to semantic schema.

Migrates old boolean fields to FindingReport tri-state values.
"""

from typing import Dict, Any, Optional
from schemas.dpm_cohort import DPMCohort
from core.types.models import FindingReport
from core.types.enums import Status, AggregationUnit


def migrate_old_data(old_data: Dict[str, Any]) -> DPMCohort:
    """
    Convert legacy dictionary to DPMCohort schema.
    
    Args:
        old_data: Dictionary matching old schema structure
        
    Returns:
        DPMCohort instance with migrated data
    """
    # 1. Base cohort identifiers
    study_id = old_data.get("study_id", "Unknown_Study")
    cohort_id = f"{study_id}_legacy"
    
    # 2. Prepare new data dict
    new_data = {
        "study_id": study_id,
        "cohort_id": cohort_id,
        "cohort_n_patients": 999,  # placeholder for unknown
        "year": old_data.get("year"),
    }
    
    # 3. Migrate binary fields
    binary_fields = [
        "ct_ground_glass", "ct_solid_nodules", "ct_central_cavitation"
        # ... add all other fields here
    ]
    
    for field in binary_fields:
        if field in old_data:
            val = old_data[field]
            if val is True:
                new_data[field] = FindingReport(
                    status=Status.PRESENT,
                    aggregation_unit=AggregationUnit.UNCLEAR
                )
            elif val is False:
                new_data[field] = FindingReport(
                    status=Status.ABSENT,
                    aggregation_unit=AggregationUnit.UNCLEAR
                )
            # None -> leave as None (optional)
            
    return DPMCohort(**new_data)

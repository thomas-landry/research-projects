"""
Tests for Schema Migration - Phase 6 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from core.types.enums import Status, AggregationUnit

# Mock old schema data structure
OLD_DATA = {
    "study_id": "Smith_2020",
    "year": 2020,
    "ct_ground_glass": True,  # Boolean
    "ct_solid_nodules": False,
    "ct_not_reported": None,
}

class TestSchemaMigration:
    """Tests for migrating old boolean schema to new semantic schema."""
    
    def test_migrate_old_schema(self):
        """Migration converts boolean fields to FindingReport."""
        from core.migration.schema_migration import migrate_old_data
        from schemas.dpm_cohort import DPMCohort
        
        new_cohort = migrate_old_data(OLD_DATA)
        
        assert isinstance(new_cohort, DPMCohort)
        
        # True -> PRESENT
        assert new_cohort.ct_ground_glass.status == Status.PRESENT
        assert new_cohort.ct_ground_glass.n is None
        assert new_cohort.ct_ground_glass.aggregation_unit == AggregationUnit.UNCLEAR
        
        # False -> ABSENT
        assert new_cohort.ct_solid_nodules.status == Status.ABSENT
        
        # None -> None (or NOT_REPORTED depending on logic, lets say None for now)
        assert new_cohort.ct_central_cavitation is None
    
    def test_migrate_preserves_identifiers(self):
        """Migration preserves study_id and creates cohort_id."""
        from core.migration.schema_migration import migrate_old_data
        
        new_cohort = migrate_old_data(OLD_DATA)
        
        assert new_cohort.study_id == "Smith_2020"
        # Since old data didn't have cohort_id, we generate one
        assert "Smith_2020" in new_cohort.cohort_id
        assert new_cohort.cohort_n_patients >= 1  # Default if unknown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

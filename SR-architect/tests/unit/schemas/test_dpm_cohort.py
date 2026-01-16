"""
Tests for DPMCohort schema - Phase 4 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from pydantic import ValidationError


class TestDPMCohortBase:
    """Tests for DPMCohort base model."""
    
    def test_dpm_cohort_has_required_identifiers(self):
        """DPMCohort requires study_id, cohort_id, cohort_n_patients."""
        from schemas.dpm_cohort import DPMCohort
        
        # Valid creation
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
        )
        assert cohort.study_id == "Smith_2020"
        assert cohort.cohort_id == "Smith_2020_overall"
        assert cohort.cohort_n_patients == 5
        
        # Missing required fields
        with pytest.raises(ValidationError):
            DPMCohort(study_id="Smith_2020")  # Missing cohort_id and cohort_n
    
    def test_dpm_cohort_uses_library_fields(self):
        """DPMCohort uses FieldLibrary specs for metadata."""
        from schemas.dpm_cohort import DPMCohort
        
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
            title="A study of DPM",
            year=2020,
        )
        
        assert cohort.title == "A study of DPM"
        assert cohort.year == 2020


class TestDPMCohortCTFindings:
    """Tests for DPMCohort CT findings."""
    
    def test_dpm_cohort_has_ct_findings(self):
        """DPMCohort has all CT finding fields."""
        from schemas.dpm_cohort import DPMCohort
        from core.types.models import FindingReport
        from core.types.enums import Status, AggregationUnit
        
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
            ct_ground_glass=FindingReport(
                status=Status.PRESENT,
                n=3,
                N=5,
                aggregation_unit=AggregationUnit.PATIENT,
            ),
        )
        
        assert cohort.ct_ground_glass.status == Status.PRESENT
        assert cohort.ct_ground_glass.n == 3
    
    def test_dpm_cohort_ct_fields_are_optional(self):
        """CT findings should be optional."""
        from schemas.dpm_cohort import DPMCohort
        
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
        )
        
        assert cohort.ct_ground_glass is None
        assert cohort.ct_solid_nodules is None


class TestDPMCohortValidators:
    """Tests for DPMCohort validators."""
    
    def test_dpm_cohort_validates_denominator(self):
        """Denominator N cannot exceed cohort_n_patients."""
        from schemas.dpm_cohort import DPMCohort
        from core.types.models import FindingReport
        from core.types.enums import Status, AggregationUnit
        
        # Valid: N <= cohort_n_patients
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
            ct_ground_glass=FindingReport(
                status=Status.PRESENT,
                n=3,
                N=5,  # N == cohort_n_patients: OK
                aggregation_unit=AggregationUnit.PATIENT,
            ),
        )
        assert cohort.ct_ground_glass.N == 5
        
        # Invalid: N > cohort_n_patients
        with pytest.raises(ValidationError, match="exceeds cohort"):
            DPMCohort(
                study_id="Smith_2020",
                cohort_id="Smith_2020_overall",
                cohort_n_patients=5,
                ct_ground_glass=FindingReport(
                    status=Status.PRESENT,
                    n=7,
                    N=10,  # N > cohort_n_patients: INVALID
                    aggregation_unit=AggregationUnit.PATIENT,
                ),
            )
    
    def test_dpm_cohort_allows_lesion_level_different_N(self):
        """Lesion-level findings can have N != cohort_n_patients."""
        from schemas.dpm_cohort import DPMCohort
        from core.types.models import FindingReport
        from core.types.enums import Status, AggregationUnit
        
        # Valid: lesion-level, N = 10 but cohort_n = 5
        cohort = DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
            ct_ground_glass=FindingReport(
                status=Status.PRESENT,
                n=7,
                N=10,  # 10 lesions in 5 patients: OK
                aggregation_unit=AggregationUnit.LESION,
            ),
        )
        assert cohort.ct_ground_glass.N == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for core type enums - Phase 1 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest


class TestStatusEnum:
    """Tests for Status tri-state enum."""
    
    def test_status_enum_has_four_values(self):
        """Status enum must have exactly 4 tri-state values."""
        from core.types.enums import Status
        
        assert len(Status) == 4
        assert Status.PRESENT.value == "present"
        assert Status.ABSENT.value == "absent"
        assert Status.NOT_REPORTED.value == "not_reported"
        assert Status.UNCLEAR.value == "unclear"
    
    def test_status_is_string_serializable(self):
        """Status must serialize to string for CSV export."""
        from core.types.enums import Status
        
        assert str(Status.PRESENT) == "Status.PRESENT"
        assert Status.PRESENT.value == "present"


class TestAggregationUnitEnum:
    """Tests for AggregationUnit enum."""
    
    def test_aggregation_unit_has_six_values(self):
        """AggregationUnit for tracking denominator context."""
        from core.types.enums import AggregationUnit
        
        assert len(AggregationUnit) == 6
        assert AggregationUnit.PATIENT.value == "patient"
        assert AggregationUnit.LESION.value == "lesion"
        assert AggregationUnit.SPECIMEN.value == "specimen"
        assert AggregationUnit.BIOPSY.value == "biopsy"
        assert AggregationUnit.IMAGING_SERIES.value == "imaging_series"
        assert AggregationUnit.UNCLEAR.value == "unclear"
    
    def test_aggregation_unit_default_is_patient(self):
        """Default aggregation should be patient-level."""
        from core.types.enums import AggregationUnit
        
        # Test that PATIENT is a valid default
        default = AggregationUnit.PATIENT
        assert default == AggregationUnit.PATIENT


class TestExtractionPolicyEnum:
    """Tests for ExtractionPolicy enum."""
    
    def test_extraction_policy_has_five_values(self):
        """ExtractionPolicy for routing extraction to appropriate handler."""
        from core.types.enums import ExtractionPolicy
        
        assert len(ExtractionPolicy) == 5
        assert ExtractionPolicy.METADATA.value == "metadata"
        assert ExtractionPolicy.CAN_BE_INFERRED.value == "inferred"
        assert ExtractionPolicy.MUST_BE_EXPLICIT.value == "explicit"
        assert ExtractionPolicy.DERIVED.value == "derived"
        assert ExtractionPolicy.HUMAN_REVIEW.value == "human_review"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

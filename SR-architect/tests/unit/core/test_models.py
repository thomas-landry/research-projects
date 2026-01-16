"""
Tests for core type models - Phase 1 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from pydantic import ValidationError


class TestFindingReport:
    """Tests for FindingReport model."""
    
    def test_finding_report_tri_state(self):
        """FindingReport captures status, n, and N."""
        from core.types.models import FindingReport
        from core.types.enums import Status, AggregationUnit
        
        finding = FindingReport(
            status=Status.PRESENT,
            n=3,
            N=5,
            aggregation_unit=AggregationUnit.PATIENT,
        )
        
        assert finding.status == Status.PRESENT
        assert finding.n == 3
        assert finding.N == 5
        assert finding.aggregation_unit == AggregationUnit.PATIENT
    
    def test_finding_report_validates_n_cannot_exceed_N(self):
        """n must not exceed N."""
        from core.types.models import FindingReport
        from core.types.enums import Status
        
        # Valid: n <= N
        f = FindingReport(status=Status.PRESENT, n=3, N=5)
        assert f.n == 3
        
        # Invalid: n > N should raise
        with pytest.raises(ValidationError):
            FindingReport(status=Status.PRESENT, n=7, N=5)
    
    def test_finding_report_validates_n_non_negative(self):
        """n must be >= 0."""
        from core.types.models import FindingReport
        
        with pytest.raises(ValidationError):
            FindingReport(n=-1, N=5)
    
    def test_finding_report_evidence_quote_optional(self):
        """Evidence quote should be optional."""
        from core.types.models import FindingReport
        from core.types.enums import Status
        
        # Without quote
        f1 = FindingReport(status=Status.PRESENT, n=3, N=5)
        assert f1.evidence_quote is None
        
        # With quote
        f2 = FindingReport(
            status=Status.PRESENT,
            n=3,
            N=5,
            evidence_quote="3 of 5 patients had..."
        )
        assert f2.evidence_quote == "3 of 5 patients had..."


class TestMeasurementData:
    """Tests for MeasurementData model."""
    
    def test_measurement_data_age_normalization(self):
        """MeasurementData captures age with normalization."""
        from core.types.models import MeasurementData
        
        age = MeasurementData(
            raw_text="median 65 (IQR 45-78)",
            value_min=45.0,
            value_max=78.0,
            value_point_estimate=65.0,
            value_unit="years",
            value_type="median",
        )
        
        assert age.raw_text == "median 65 (IQR 45-78)"
        assert age.value_point_estimate == 65.0
        assert age.value_unit == "years"
    
    def test_measurement_data_followup_normalization(self):
        """MeasurementData captures follow-up duration."""
        from core.types.models import MeasurementData
        
        followup = MeasurementData(
            raw_text="24 months (range 6-60)",
            value_min=6.0,
            value_max=60.0,
            value_point_estimate=24.0,
            value_unit="months",
        )
        
        assert followup.value_unit == "months"
        assert followup.value_min == 6.0


class TestCountData:
    """Tests for CountData model."""
    
    def test_count_data_patient_count(self):
        """CountData captures patient count."""
        from core.types.models import CountData
        
        count = CountData(
            raw_text="5 patients",
            count_value=5,
            count_unit="patients",
        )
        
        assert count.count_value == 5
        assert count.count_unit == "patients"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

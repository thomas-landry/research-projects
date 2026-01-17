"""
Tests for Baseline Measurement with FindingReport - Phase 0.

Verifies that accuracy metrics work with the new FindingReport schema.
"""

import pytest
from core.types.models import FindingReport
from core.types.enums import Status, AggregationUnit

class TestFindingReportAccuracy:
    """Tests accuracy calculation for FindingReport objects."""
    
    def test_calculate_accuracy_matches_status(self):
        """
        GIVEN predictions and gold standard as FindingReport objects
        WHEN calculating field accuracy
        THEN accuracy is based on matching Status
        """
        from core.metrics.baseline_measurement import calculate_field_accuracy
        
        # Exact match (PRESENT == PRESENT)
        predictions = [
            {"ct_ggo": FindingReport(status=Status.PRESENT, n=5, N=10)}
        ]
        gold_standard = [
            {"ct_ggo": FindingReport(status=Status.PRESENT, n=5, N=10)}
        ]
        
        acc = calculate_field_accuracy(predictions, gold_standard, "ct_ggo")
        assert acc == 1.0
        
        # Mismatch (PRESENT != ABSENT)
        predictions = [
            {"ct_ggo": FindingReport(status=Status.PRESENT)}
        ]
        gold_standard = [
            {"ct_ggo": FindingReport(status=Status.ABSENT)}
        ]
        
        acc = calculate_field_accuracy(predictions, gold_standard, "ct_ggo")
        assert acc == 0.0
    
    def test_calculate_accuracy_handles_status_vs_string(self):
        """
        GIVEN prediction as FindingReport and gold as string (legacy compat)
        WHEN calculating accuracy
        THEN it handles comparison gracefully (e.g. by converting or failing)
        """
        # Decisions need to be made here. For now, strict type matching or robust comparison?
        # Let's assume we require the pipeline to produce FindingReport, so gold standard should also be FindingReport.
        pass

    def test_calculate_accuracy_ignores_frequencies_for_binary_metric(self):
        """
        GIVEN matching status but differing n/N
        WHEN calculating *binary* accuracy
        THEN it is counted as correct
        """
        from core.metrics.baseline_measurement import calculate_field_accuracy
        
        # Status matches (PRESENT), but n differs (5 vs 6)
        predictions = [
            {"ct_ggo": FindingReport(status=Status.PRESENT, n=5)}
        ]
        gold_standard = [
            {"ct_ggo": FindingReport(status=Status.PRESENT, n=6)}
        ]
        
        acc = calculate_field_accuracy(predictions, gold_standard, "ct_ggo")
        assert acc == 1.0

    def test_full_report_generation_with_finding_report(self):
        """
        GIVEN predictions and gold standard with FindingReport objects
        WHEN generating baseline report
        THEN report matches expected structure and accuracy
        """
        from core.metrics.baseline_measurement import BaselineMeasurement
        from core.types.models import FindingReport
        from core.types.enums import Status
        
        # 2 fields, 1 tier
        tier_config = {
            1: ["ct_ggo", "ct_nodules"]
        }
        
        # Case 1: Perfect match
        pred1 = {
            "ct_ggo": FindingReport(status=Status.PRESENT, n=5),
            "ct_nodules": FindingReport(status=Status.ABSENT)
        }
        gold1 = {
            "ct_ggo": FindingReport(status=Status.PRESENT, n=5),
            "ct_nodules": FindingReport(status=Status.ABSENT)
        }
        
        # Case 2: Partial match
        # GGO: Pred=ABSENT, Gold=PRESENT (Mismatch)
        # Nodules: Pred=PRESENT, Gold=PRESENT (Match)
        pred2 = {
            "ct_ggo": FindingReport(status=Status.ABSENT),
            "ct_nodules": FindingReport(status=Status.PRESENT)
        }
        gold2 = {
            "ct_ggo": FindingReport(status=Status.PRESENT),
            "ct_nodules": FindingReport(status=Status.PRESENT)
        }
        
        predictions = [pred1, pred2]
        gold_standard = [gold1, gold2]
        
        measurement = BaselineMeasurement(tier_config)
        report = measurement.generate_report(predictions, gold_standard)
        
        # GGO: 1/2 correct = 0.5
        assert report["field_accuracies"]["ct_ggo"] == 0.5
        
        # Nodules: 2/2 correct = 1.0
        assert report["field_accuracies"]["ct_nodules"] == 1.0
        
        # Tier 1: (0.5 + 1.0) / 2 = 0.75
        assert report["tier_accuracies"][1] == 0.75


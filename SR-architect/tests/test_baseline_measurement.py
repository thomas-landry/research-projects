"""
Tests for Baseline Measurement - Phase 0 Binary Extraction Accuracy.

TDD: Write tests first, then implement BaselineMeasurement class.
"""

import pytest
from typing import Dict, Any, List, Optional


class TestBaselineMeasurement:
    """Tests for per-field and per-tier accuracy measurement."""
    
    def test_field_accuracy_calculates_correctly(self):
        """
        GIVEN predictions and gold standard for a field
        WHEN calculating field accuracy
        THEN accuracy = correct / total
        """
        from core.metrics.baseline_measurement import calculate_field_accuracy
        
        # Single field, all correct
        predictions = [{"field1": True}, {"field1": True}]
        gold_standard = [{"field1": True}, {"field1": True}]
        
        accuracy = calculate_field_accuracy(predictions, gold_standard, "field1")
        assert accuracy == 1.0
        
        # Single field, 50% correct
        predictions = [{"field1": True}, {"field1": False}]
        gold_standard = [{"field1": True}, {"field1": True}]
        
        accuracy = calculate_field_accuracy(predictions, gold_standard, "field1")
        assert accuracy == 0.5
        
        # Single field, 0% correct
        predictions = [{"field1": False}]
        gold_standard = [{"field1": True}]
        
        accuracy = calculate_field_accuracy(predictions, gold_standard, "field1")
        assert accuracy == 0.0
    
    def test_field_accuracy_handles_null_values(self):
        """
        GIVEN predictions with NULL values
        WHEN calculating field accuracy
        THEN NULL != any value (treated as incorrect)
        """
        from core.metrics.baseline_measurement import calculate_field_accuracy
        
        # NULL prediction vs True gold
        predictions = [{"field1": None}]
        gold_standard = [{"field1": True}]
        
        accuracy = calculate_field_accuracy(predictions, gold_standard, "field1")
        assert accuracy == 0.0
        
        # NULL prediction vs NULL gold (both NULL = match)
        predictions = [{"field1": None}]
        gold_standard = [{"field1": None}]
        
        accuracy = calculate_field_accuracy(predictions, gold_standard, "field1")
        assert accuracy == 1.0
    
    def test_tier_accuracy_aggregates_correctly(self):
        """
        GIVEN field accuracies and tier configuration
        WHEN calculating tier accuracy
        THEN tier accuracy = average of field accuracies in tier
        """
        from core.metrics.baseline_measurement import calculate_tier_accuracy
        
        field_accuracies = {
            "field1": 0.9,
            "field2": 0.8,
            "field3": 0.7,
            "field4": 0.6,
        }
        
        tier_config = {
            1: ["field1", "field2"],  # Tier 1 fields
            2: ["field3", "field4"],  # Tier 2 fields
        }
        
        tier1_accuracy = calculate_tier_accuracy(field_accuracies, tier_config, tier=1)
        assert tier1_accuracy == pytest.approx(0.85)  # (0.9 + 0.8) / 2
        
        tier2_accuracy = calculate_tier_accuracy(field_accuracies, tier_config, tier=2)
        assert tier2_accuracy == pytest.approx(0.65)  # (0.7 + 0.6) / 2
    
    def test_null_rate_calculated(self):
        """
        GIVEN extraction data with some NULL values
        WHEN calculating NULL rate
        THEN null_rate = null_count / total
        """
        from core.metrics.baseline_measurement import calculate_null_rate
        
        data = [
            {"field1": None},
            {"field1": "value"},
            {"field1": None},
            {"field1": "value"},
        ]
        
        null_rate = calculate_null_rate(data, "field1")
        assert null_rate == 0.5  # 2 NULL out of 4
        
        # All NULL
        data = [{"field1": None}, {"field1": None}]
        null_rate = calculate_null_rate(data, "field1")
        assert null_rate == 1.0
        
        # No NULL
        data = [{"field1": "a"}, {"field1": "b"}]
        null_rate = calculate_null_rate(data, "field1")
        assert null_rate == 0.0
    
    def test_report_includes_all_metrics(self):
        """
        GIVEN predictions and gold standard
        WHEN generating baseline report
        THEN report includes per-field accuracy, per-tier accuracy, NULL rates
        """
        from core.metrics.baseline_measurement import BaselineMeasurement
        
        predictions = [
            {"symptom_fever": True, "ct_ground_glass": True, "age": 65},
            {"symptom_fever": False, "ct_ground_glass": None, "age": None},
        ]
        
        gold_standard = [
            {"symptom_fever": True, "ct_ground_glass": True, "age": 65},
            {"symptom_fever": True, "ct_ground_glass": True, "age": 70},
        ]
        
        tier_config = {
            1: ["symptom_fever"],
            2: ["ct_ground_glass"],
            3: ["age"],
        }
        
        measurement = BaselineMeasurement(tier_config)
        report = measurement.generate_report(predictions, gold_standard)
        
        # Report structure
        assert "field_accuracies" in report
        assert "tier_accuracies" in report
        assert "null_rates" in report
        assert "worst_performing_fields" in report
        
        # Field accuracies present
        assert "symptom_fever" in report["field_accuracies"]
        assert "ct_ground_glass" in report["field_accuracies"]
        assert "age" in report["field_accuracies"]
        
        # Tier accuracies present
        assert 1 in report["tier_accuracies"]
        assert 2 in report["tier_accuracies"]
        assert 3 in report["tier_accuracies"]
        
        # NULL rates present
        assert "ct_ground_glass" in report["null_rates"]
        assert "age" in report["null_rates"]


class TestRuleCoverageAudit:
    """Tests for binary field rule coverage audit."""
    
    def test_audit_identifies_all_binary_fields(self):
        """
        GIVEN a schema with binary fields
        WHEN auditing rule coverage
        THEN all binary fields are identified
        """
        from core.binary.coverage_audit import get_binary_fields
        
        # Use actual schema
        from schemas.dpm_gold_standard import DPMGoldStandardSchema
        
        binary_fields = get_binary_fields(DPMGoldStandardSchema)
        
        # Should find 80+ binary fields
        assert len(binary_fields) >= 70
        
        # Spot check known binary fields
        assert "symptom_fever" in binary_fields
        assert "ct_ground_glass" in binary_fields
        assert "ihc_ema_pos" in binary_fields
        assert "biopsy_tblb" in binary_fields
    
    def test_audit_maps_rules_to_fields(self):
        """
        GIVEN existing derivation rules
        WHEN auditing coverage
        THEN rules are correctly mapped to fields
        """
        from core.binary.coverage_audit import audit_rule_coverage
        from core.binary.rules import ALL_RULES
        
        coverage = audit_rule_coverage(ALL_RULES)
        
        # Should map existing rules
        assert "symptom_fever" in coverage
        assert coverage["symptom_fever"]["has_rule"] == True
        
        assert "ct_ground_glass" in coverage
        assert coverage["ct_ground_glass"]["has_rule"] == True
    
    def test_gaps_identified_correctly(self):
        """
        GIVEN schema fields and rules
        WHEN identifying gaps
        THEN uncovered fields are returned
        """
        from core.binary.coverage_audit import identify_gaps
        from schemas.dpm_gold_standard import DPMGoldStandardSchema
        from core.binary.rules import ALL_RULES
        
        gaps = identify_gaps(DPMGoldStandardSchema, ALL_RULES)
        
        # Should find gaps (actual count is around 16)
        assert len(gaps) >= 10
        
        # Known gaps from analysis
        # (Some biopsy diagnostic fields are likely uncovered)
        # We'll verify exact fields after running


class TestFieldTierConfiguration:
    """Tests for field tier classification."""
    
    def test_load_tier_config(self):
        """
        GIVEN a tier configuration YAML file
        WHEN loading configuration
        THEN all tiers are loaded with fields and thresholds
        """
        from core.extraction.tier_config import load_tier_config
        
        config = load_tier_config("config/field_tiers.yaml")
        
        # Should have 5 tiers
        assert len(config["tiers"]) == 5
        
        # Each tier should have confidence threshold and fields
        for tier_num in range(1, 6):
            tier = config["tiers"][tier_num]
            assert "confidence_threshold" in tier
            assert "fields" in tier
            assert isinstance(tier["fields"], list)
    
    def test_get_field_tier(self):
        """
        GIVEN a tier configuration
        WHEN getting tier for a field
        THEN correct tier is returned
        """
        from core.extraction.tier_config import get_field_tier
        
        config = {
            "tiers": {
                1: {"fields": ["symptom_fever", "symptom_dyspnea"]},
                2: {"fields": ["ct_ground_glass"]},
                3: {"fields": ["age"]},
            }
        }
        
        assert get_field_tier("symptom_fever", config) == 1
        assert get_field_tier("ct_ground_glass", config) == 2
        assert get_field_tier("age", config) == 3
        assert get_field_tier("unknown_field", config) is None
    
    def test_get_confidence_threshold(self):
        """
        GIVEN a tier configuration
        WHEN getting confidence threshold for a tier
        THEN correct threshold is returned
        """
        from core.extraction.tier_config import get_confidence_threshold
        
        config = {
            "tiers": {
                1: {"confidence_threshold": 0.90, "fields": []},
                2: {"confidence_threshold": 0.85, "fields": []},
                3: {"confidence_threshold": 0.70, "fields": []},
            }
        }
        
        assert get_confidence_threshold(1, config) == 0.90
        assert get_confidence_threshold(2, config) == 0.85
        assert get_confidence_threshold(3, config) == 0.70


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

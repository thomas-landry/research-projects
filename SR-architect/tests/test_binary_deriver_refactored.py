"""
Tests for BinaryDeriver (refactored).
"""
import pytest
from core.binary import BinaryDeriver, process_extraction, DerivationRule

def test_binary_deriver_initialization():
    deriver = BinaryDeriver()
    assert len(deriver.rules) > 0

def test_derivation_logic():
    deriver = BinaryDeriver()
    
    # Test case from docstring
    sample = {
        "symptom_narrative": "Patient presented with dyspnea and non-productive cough.",
        "associated_conditions_narrative": "History of breast cancer.",
        "ct_narrative": "Ground-glass opacities.",
        "outcomes": "Stable.",
    }
    
    derived = deriver.derive_all(sample)
    
    assert derived.get("symptom_dyspnea") is True
    assert derived.get("symptom_cough_dry") is True
    assert derived.get("assoc_extrapulmonary_ca") is True
    assert derived.get("ct_ground_glass") is True
    assert derived.get("outcome_dpm_stable") is True
    
    # Test negative case
    assert derived.get("symptom_fever") is None

def test_process_extraction_integration():
    sample = {
        "symptom_narrative": "Dyspnea.",
        "existing_field": "value"
    }
    
    result = process_extraction(sample)
    
    assert "symptom_dyspnea" in result
    assert result["symptom_dyspnea"] is True
    assert result["existing_field"] == "value"

def test_shim_compatibility():
    # Verify we can import from the shim location
    from core.binary_deriver import BinaryDeriver as ShimDeriver
    deriver = ShimDeriver()
    assert isinstance(deriver, BinaryDeriver)

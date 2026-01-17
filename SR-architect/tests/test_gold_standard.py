"""
Tests for Gold Standard Management.

Verifies loading, saving, and validation of gold standard datasets.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

class TestGoldStandardManagement:
    """Tests for GoldStandard class."""
    
    def test_load_golden_file_validates_schema(self):
        """
        GIVEN a JSON file representing a cohort
        WHEN loading as gold standard
        THEN it is validated against DPMCohort schema
        """
        from core.metrics.gold_standard import GoldStandard
        from schemas.dpm_cohort import DPMCohort
        
        # Valid data
        valid_data = {
            "study_id": "Smith_2020",
            "cohort_id": "Smith_2020_A",
            "cohort_n_patients": 100,
            "ct_ground_glass": {
                "status": "present",
                "n": 10,
                "N": 100,
                "aggregation_unit": "patient"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_data, f)
            path = f.name
            
        try:
            gs = GoldStandard.load_file(path)
            assert isinstance(gs, DPMCohort)
            assert gs.study_id == "Smith_2020"
        finally:
            os.remove(path)
            
    def test_load_golden_file_fails_invalid_schema(self):
        """
        GIVEN invalid JSON data
        WHEN loading
        THEN validation error is raised
        """
        from core.metrics.gold_standard import GoldStandard
        import pydantic
        
        invalid_data = {
            "study_id": "Smith_2020"
            # Missing required fields
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            path = f.name
            
        try:
            with pytest.raises(pydantic.ValidationError):
                GoldStandard.load_file(path)
        finally:
            os.remove(path)


"""
Gold Standard Management.

Handles loading, saving, and validation of gold standard datasets against the semantic schema.
"""

import json
from pathlib import Path
from typing import List, Union, Dict
from schemas.dpm_cohort import DPMCohort

class GoldStandard:
    """Utilities for managing Gold Standard datasets."""
    
    @staticmethod
    def load_file(path: Union[str, Path]) -> DPMCohort:
        """
        Load a single gold standard file (JSON).
        
        Args:
            path: Path to JSON file
            
        Returns:
            Validated DPMCohort object
            
        Raises:
            ValidationError: If data does not match schema
            FileNotFoundError: If file not found
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Gold standard file not found: {path}")
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        return DPMCohort(**data)

    @staticmethod
    def load_directory(directory: Union[str, Path]) -> List[DPMCohort]:
        """
        Load all JSON files in a directory.
        
        Args:
            directory: Path to directory
            
        Returns:
            List of DPMCohort objects
        """
        directory = Path(directory)
        cohorts = []
        for file_path in directory.glob("*.json"):
            try:
                cohorts.append(GoldStandard.load_file(file_path))
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        return cohorts

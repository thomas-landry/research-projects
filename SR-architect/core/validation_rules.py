"""
Validation Rules for extracted data.

Implements range checks, cross-field validation, and study-type-aware rules
per spec.md validation configuration.
"""
import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from core.utils import get_logger

logger = get_logger("ValidationRules")


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    field_name: str = ""
    message: str = ""
    original_value: Any = None
    
    
# Default range validation rules per spec.md
RANGE_RULES: Dict[str, tuple] = {
    "sample_size": (1, 100000),
    "enrolled_n": (1, 100000),
    "analyzed_n": (1, 100000),
    "mean_age": (0, 120),
    "min_age": (0, 120),
    "max_age": (0, 120),
    "median_age": (0, 120),
    "follow_up_months": (0, 600),
    "follow_up_days": (0, 18000),
    "mortality_rate": (0, 1),
    "survival_rate": (0, 1),
    "response_rate": (0, 1),
    "publication_year": (1900, 2030),
}

# Cross-field validation rules
CROSS_FIELD_RULES = [
    # analyzed_n should be <= enrolled_n
    {
        "name": "analyzed_vs_enrolled",
        "fields": ["analyzed_n", "enrolled_n"],
        "rule": lambda data: data.get("analyzed_n", 0) <= data.get("enrolled_n", float('inf')),
        "message": "analyzed_n should not exceed enrolled_n",
    },
    # min_age <= mean_age <= max_age
    {
        "name": "age_consistency",
        "fields": ["min_age", "mean_age", "max_age"],
        "rule": lambda data: (
            data.get("min_age", 0) <= data.get("mean_age", 50) <= data.get("max_age", 120)
            if all(k in data for k in ["min_age", "mean_age", "max_age"])
            else True
        ),
        "message": "Age values should satisfy: min_age <= mean_age <= max_age",
    },
]

# Study-type-aware required fields
STUDY_TYPE_REQUIRED_FIELDS = {
    "RCT": ["randomization_method", "blinding"],
    "Cohort": ["comparator_description"],
    "Case_Report": [],  # sample_size optional
    "Meta_Analysis": ["included_studies_count"],
}


class ValidationRules:
    """
    Validates extracted data against predefined rules.
    
    Checks:
    - Range validation (e.g., sample_size 1-100000)
    - Cross-field validation (e.g., analyzed_n <= enrolled_n)
    - Study-type-aware validation (e.g., RCT requires randomization)
    """
    
    def __init__(
        self,
        range_rules: Optional[Dict[str, tuple]] = None,
        cross_field_rules: Optional[List[Dict]] = None,
    ):
        """
        Initialize validator with optional custom rules.
        
        Args:
            range_rules: Custom range rules {field: (min, max)}
            cross_field_rules: Custom cross-field rules
        """
        self.range_rules = range_rules or RANGE_RULES
        self.cross_field_rules = cross_field_rules or CROSS_FIELD_RULES
        
    def validate_field(
        self, 
        field_name: str, 
        value: Any,
        strict: bool = True,
    ) -> ValidationResult:
        """
        Validate a single field value.
        
        Args:
            field_name: Name of the field
            value: Extracted value
            strict: If True, None/empty values fail validation
            
        Returns:
            ValidationResult with is_valid status
        """
        # Handle None/empty
        if value is None or value == "":
            if strict:
                return ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    message=f"Field '{field_name}' is empty or None",
                    original_value=value,
                )
            return ValidationResult(is_valid=True, field_name=field_name)
        
        # Range check if applicable
        if field_name in self.range_rules:
            min_val, max_val = self.range_rules[field_name]
            
            try:
                numeric_value = float(value)
                if not (min_val <= numeric_value <= max_val):
                    return ValidationResult(
                        is_valid=False,
                        field_name=field_name,
                        message=f"Value {value} out of range [{min_val}, {max_val}]",
                        original_value=value,
                    )
            except (ValueError, TypeError):
                return ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    message=f"Cannot validate non-numeric value for '{field_name}'",
                    original_value=value,
                )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            original_value=value,
        )
    
    def validate_cross_field(
        self,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate cross-field relationships.
        
        Args:
            data: Dictionary of extracted fields
            
        Returns:
            ValidationResult (first failure or success)
        """
        for rule in self.cross_field_rules:
            # Check if all required fields are present
            if not all(f in data for f in rule["fields"]):
                continue
                
            if not rule["rule"](data):
                return ValidationResult(
                    is_valid=False,
                    field_name=",".join(rule["fields"]),
                    message=rule["message"],
                )
        
        return ValidationResult(is_valid=True, message="All cross-field checks passed")
    
    def validate_study_type(
        self,
        data: Dict[str, Any],
        study_type: str,
    ) -> ValidationResult:
        """
        Validate study-type-specific required fields.
        
        Args:
            data: Extracted data
            study_type: Type of study (RCT, Cohort, etc.)
            
        Returns:
            ValidationResult with missing fields info
        """
        required = STUDY_TYPE_REQUIRED_FIELDS.get(study_type, [])
        missing = [f for f in required if f not in data or data[f] is None]
        
        if missing:
            return ValidationResult(
                is_valid=False,
                field_name=study_type,
                message=f"Missing required fields for {study_type}: {missing}",
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_all(
        self,
        data: Dict[str, Any],
        study_type: Optional[str] = None,
    ) -> List[ValidationResult]:
        """
        Run all validations on extracted data.
        
        Args:
            data: All extracted fields
            study_type: Optional study type for type-specific checks
            
        Returns:
            List of all validation results (including failures)
        """
        results = []
        
        # Range validation for all fields
        for field_name, value in data.items():
            result = self.validate_field(field_name, value, strict=False)
            if not result.is_valid:
                results.append(result)
        
        # Cross-field validation
        cross_result = self.validate_cross_field(data)
        if not cross_result.is_valid:
            results.append(cross_result)
        
        # Study-type validation
        if study_type:
            type_result = self.validate_study_type(data, study_type)
            if not type_result.is_valid:
                results.append(type_result)
        
        return results

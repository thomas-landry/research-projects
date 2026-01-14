"""
Auto-Corrector for common extraction errors.

Implements automatic fixes for:
- OCR errors (l→1, O→0)
- Thousands separator removal
- Percentage normalization
- Year extraction from date strings

Per spec.md AUTO_CORRECTIONS configuration.
"""
import re
from typing import Any, Optional, List, Tuple, Union
from dataclasses import dataclass

from core.utils import get_logger

logger = get_logger("AutoCorrector")


@dataclass
class CorrectionResult:
    """Result of an auto-correction attempt."""
    original_value: Any
    corrected_value: Any
    correction_type: Optional[str] = None
    was_corrected: bool = False
    
    def __post_init__(self):
        self.was_corrected = self.correction_type is not None


# OCR correction patterns per spec.md
OCR_PATTERNS: List[Tuple[str, str]] = [
    (r'l(\d+)', r'1\1'),      # l→1 at start of number
    (r'(\d+)l', r'\g<1>1'),   # l→1 at end of number
    (r'O(\d+)', r'0\1'),      # O→0 at start
    (r'(\d+)O', r'\g<1>0'),   # O→0 at end
    (r'(\d+),(\d{3})', r'\1\2'),  # Remove thousands separator
]

# Fields that should be rates (0-1)
RATE_FIELDS = [
    "mortality_rate",
    "survival_rate", 
    "response_rate",
    "recurrence_rate",
    "complication_rate",
]

# Fields that are percentages but stored as decimals
PERCENTAGE_FIELDS = RATE_FIELDS


class AutoCorrector:
    """
    Automatically corrects common extraction errors.
    
    Corrections are logged for audit trail.
    """
    
    def __init__(self):
        """Initialize corrector with default patterns."""
        self.corrections_applied = []
        
    def correct(
        self,
        field_name: str,
        value: Any,
    ) -> CorrectionResult:
        """
        Apply auto-corrections to a value.
        
        Args:
            field_name: Name of the field
            value: Extracted value
            
        Returns:
            CorrectionResult with corrected value
        """
        if value is None:
            return CorrectionResult(value, value)
        
        original = value
        corrected = value
        correction_type = None
        
        # String-based corrections
        if isinstance(value, str):
            corrected, correction_type = self._correct_string(field_name, value)
        
        # Numeric corrections
        elif isinstance(value, (int, float)):
            corrected, correction_type = self._correct_numeric(field_name, value)
        
        if correction_type:
            self._log_correction(field_name, original, corrected, correction_type)
        
        return CorrectionResult(
            original_value=original,
            corrected_value=corrected,
            correction_type=correction_type,
        )
    
    def _correct_string(
        self,
        field_name: str,
        value: str,
    ) -> Tuple[Any, Optional[str]]:
        """Apply string-based corrections."""
        corrected = value
        correction_type = None
        
        # OCR fixes for numeric fields
        if self._is_numeric_field(field_name):
            for pattern, replacement in OCR_PATTERNS:
                new_value = re.sub(pattern, replacement, corrected)
                if new_value != corrected:
                    corrected = new_value
                    correction_type = "ocr_fix"
        
        # Thousands separator removal
        if re.match(r'^\d{1,3}(,\d{3})+$', corrected):
            corrected = corrected.replace(',', '')
            correction_type = "thousands_separator"
        
        return corrected, correction_type
    
    def _correct_numeric(
        self,
        field_name: str,
        value: Union[int, float],
    ) -> Tuple[Any, Optional[str]]:
        """Apply numeric corrections."""
        corrected = value
        correction_type = None
        
        # Percentage to decimal normalization for rate fields
        if field_name in PERCENTAGE_FIELDS:
            if value > 1 and value <= 100:
                corrected = value / 100
                correction_type = "percentage_to_decimal"
        
        return corrected, correction_type
    
    def _is_numeric_field(self, field_name: str) -> bool:
        """Check if field should contain numeric data."""
        numeric_patterns = [
            "size", "count", "age", "year", "month", "day",
            "rate", "ratio", "percentage", "number", "_n",
        ]
        return any(p in field_name.lower() for p in numeric_patterns)
    
    def _log_correction(
        self,
        field_name: str,
        original: Any,
        corrected: Any,
        correction_type: str,
    ) -> None:
        """Log correction for audit trail."""
        entry = {
            "field": field_name,
            "original": original,
            "corrected": corrected,
            "type": correction_type,
        }
        self.corrections_applied.append(entry)
        logger.info(f"Auto-corrected {field_name}: {original} → {corrected} ({correction_type})")
    
    def correct_all(
        self,
        data: dict,
    ) -> Tuple[dict, List[CorrectionResult]]:
        """
        Apply corrections to all fields in a dictionary.
        
        Args:
            data: Dictionary of extracted fields
            
        Returns:
            Tuple of (corrected_data, list_of_corrections)
        """
        corrected_data = {}
        corrections = []
        
        for field_name, value in data.items():
            result = self.correct(field_name, value)
            corrected_data[field_name] = result.corrected_value
            if result.was_corrected:
                corrections.append(result)
        
        return corrected_data, corrections
    
    def get_correction_summary(self) -> dict:
        """Get summary of all corrections applied."""
        by_type = {}
        for c in self.corrections_applied:
            t = c["type"]
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_corrections": len(self.corrections_applied),
            "by_type": by_type,
            "corrections": self.corrections_applied,
        }
    
    def reset(self) -> None:
        """Reset correction history."""
        self.corrections_applied = []

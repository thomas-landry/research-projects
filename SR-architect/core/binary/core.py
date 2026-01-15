"""
Core logic for binary field derivation.
"""
import re
from typing import Dict, Any, Optional, List, Tuple

from .rules import DerivationRule, ALL_RULES


class BinaryDeriver:
    """
    Derive binary fields from narrative text.
    
    Usage:
        deriver = BinaryDeriver()
        extracted = {"symptom_narrative": "Patient presented with dyspnea and dry cough"}
        derived = deriver.derive_all(extracted)
        # derived = {"symptom_dyspnea": True, "symptom_cough_dry": True, ...}
    """
    
    def __init__(self, rules: List[DerivationRule] = None):
        """Initialize with rules."""
        self.rules = rules or ALL_RULES
    
    def check_pattern(self, text: str, pattern: str, case_sensitive: bool = False) -> bool:
        """Check if pattern matches in text."""
        if not text:
            return False
        flags = 0 if case_sensitive else re.IGNORECASE
        return bool(re.search(pattern, text, flags))
    
    def derive_field(
        self, 
        rule: DerivationRule, 
        narratives: Dict[str, Any]
    ) -> Tuple[str, Optional[bool]]:
        """
        Derive a single binary field from narratives.
        
        Returns:
            Tuple of (field_name, derived_value)
        """
        source_text = narratives.get(rule.source_narrative, "")
        
        if not source_text:
            return rule.field_name, None
        
        # Check positive patterns
        for pattern in rule.positive_patterns:
            if self.check_pattern(source_text, pattern, rule.case_sensitive):
                return rule.field_name, True
        
        # Check negative patterns if defined
        if rule.negative_patterns:
            for pattern in rule.negative_patterns:
                if self.check_pattern(source_text, pattern, rule.case_sensitive):
                    return rule.field_name, False
        
        # No match found
        return rule.field_name, None
    
    def derive_all(self, narratives: Dict[str, Any]) -> Dict[str, Optional[bool]]:
        """
        Derive all binary fields from narrative dict.
        
        Args:
            narratives: Dict with narrative field values
            
        Returns:
            Dict of binary field names to derived values
        """
        derived = {}
        for rule in self.rules:
            field_name, value = self.derive_field(rule, narratives)
            derived[field_name] = value
        return derived
    
    def merge_with_extraction(
        self,
        extracted: Dict[str, Any],
        derived: Dict[str, Optional[bool]],
    ) -> Dict[str, Any]:
        """
        Merge derived binaries with extracted data.
        
        Derived values only fill in missing fields (don't override).
        
        Args:
            extracted: Original extracted data
            derived: Derived binary values
            
        Returns:
            Merged dict
        """
        result = dict(extracted)
        for field, value in derived.items():
            # Only fill if not already set
            if field not in result or result[field] is None:
                result[field] = value
        return result


def process_extraction(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process extraction by deriving binary fields.
    
    Args:
        extracted_data: LLM-extracted narrative data
        
    Returns:
        Complete data with binaries derived
    """
    deriver = BinaryDeriver()
    derived = deriver.derive_all(extracted_data)
    return deriver.merge_with_extraction(extracted_data, derived)

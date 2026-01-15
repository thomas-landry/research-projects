#!/usr/bin/env python3
"""
Shim for backward compatibility.
DEPRECATED: Use core.binary instead.
"""

from .binary import BinaryDeriver, process_extraction, DerivationRule, ALL_RULES
from .binary.rules import (
    SYMPTOM_RULES,
    ASSOCIATION_RULES,
    CT_RULES,
    IHC_RULES,
    BIOPSY_RULES,
    OUTCOME_RULES,
    PATHOLOGY_RULES
)

__all__ = [
    "BinaryDeriver", 
    "process_extraction", 
    "DerivationRule", 
    "ALL_RULES",
    "SYMPTOM_RULES",
    "ASSOCIATION_RULES",
    "CT_RULES",
    "IHC_RULES",
    "BIOPSY_RULES",
    "OUTCOME_RULES",
    "PATHOLOGY_RULES"
]

if __name__ == "__main__":
    # simple test
    deriver = BinaryDeriver()
    print("BinaryDeriver initialized (via compatibility shim).")

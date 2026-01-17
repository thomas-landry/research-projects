#!/usr/bin/env python3
"""
Test for evidence extraction model validation.

Reproduces the bug where LLM returns simple strings but model expects EvidenceItem objects.
"""

import pytest
from pydantic import ValidationError
from core.extractors.models import EvidenceResponse, EvidenceItem


def test_evidence_response_accepts_simple_strings():
    """
    Test that EvidenceResponse can handle simple string arrays from LLM.
    
    This reproduces the bug where Gemini returns:
    {"evidence": ["quote1", "quote2", ""]}
    
    But the model expects:
    {"evidence": [{"field_name": "...", "extracted_value": "...", ...}, ...]}
    """
    # This is what the LLM actually returns
    llm_response = {
        "evidence": [
            "A 61-year-old female",
            "Minute pulmonary meningothelial-like nodules",
            "Bronchoscopy with transbronchial cryo biopsy",
            ""  # Empty strings are common
        ]
    }
    
    # This should NOT raise ValidationError
    response = EvidenceResponse(**llm_response)
    
    # Verify it parsed correctly
    assert len(response.evidence) == 4
    assert isinstance(response.evidence[0], EvidenceItem)
    assert response.evidence[0].exact_quote == "A 61-year-old female"


def test_evidence_response_accepts_full_objects():
    """Test that the model still accepts the full EvidenceItem format."""
    full_response = {
        "evidence": [
            {
                "field_name": "patient_age",
                "extracted_value": "61",
                "exact_quote": "A 61-year-old female",
                "confidence": 0.95
            }
        ]
    }
    
    response = EvidenceResponse(**full_response)
    assert len(response.evidence) == 1
    assert response.evidence[0].field_name == "patient_age"
    assert response.evidence[0].exact_quote == "A 61-year-old female"


def test_evidence_response_handles_empty_strings():
    """Test that empty strings in evidence array are handled gracefully."""
    response_with_empties = {
        "evidence": ["valid quote", "", "another quote", ""]
    }
    
    response = EvidenceResponse(**response_with_empties)
    assert len(response.evidence) == 4
    # Empty strings should be preserved
    assert response.evidence[1].exact_quote == ""

"""
Tests for extractor models.

TDD RED PHASE: These tests will FAIL because core/extractors/models.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from pydantic import ValidationError
from core.extractors.models import EvidenceItem, ExtractionWithEvidence, EvidenceResponse


class TestEvidenceItem:
    """Test EvidenceItem model."""
    
    def test_evidence_item_creation_minimal(self):
        """Should create EvidenceItem with minimal required fields."""
        item = EvidenceItem(
            field_name="doi",
            extracted_value="10.1234/test"
        )
        assert item.field_name == "doi"
        assert item.extracted_value == "10.1234/test"
        assert item.exact_quote == ""  # Default
        assert item.confidence == 0.9  # Default
    
    def test_evidence_item_creation_full(self):
        """Should create EvidenceItem with all fields."""
        item = EvidenceItem(
            field_name="doi",
            extracted_value="10.1234/test",
            exact_quote="DOI: 10.1234/test",
            page_number=1,
            chunk_index=0,
            start_char=100,
            end_char=120,
            confidence=0.95
        )
        assert item.field_name == "doi"
        assert item.extracted_value == "10.1234/test"
        assert item.exact_quote == "DOI: 10.1234/test"
        assert item.page_number == 1
        assert item.chunk_index == 0
        assert item.start_char == 100
        assert item.end_char == 120
        assert item.confidence == 0.95
    
    def test_coerce_quote_to_string_none(self):
        """Should coerce None exact_quote to empty string."""
        item = EvidenceItem(
            field_name="test",
            extracted_value="value",
            exact_quote=None  # Will be coerced to ""
        )
        assert item.exact_quote == ""
        assert isinstance(item.exact_quote, str)
    
    def test_coerce_quote_to_string_number(self):
        """Should coerce non-string values to string."""
        item = EvidenceItem(
            field_name="test",
            extracted_value="value",
            exact_quote=12345  # Will be coerced to "12345"
        )
        assert item.exact_quote == "12345"
        assert isinstance(item.exact_quote, str)
    
    def test_confidence_bounds(self):
        """Should enforce confidence bounds [0.0, 1.0]."""
        # Valid confidence
        item = EvidenceItem(
            field_name="test",
            extracted_value="value",
            confidence=0.5
        )
        assert item.confidence == 0.5
        
        # Out of bounds should raise validation error
        with pytest.raises(ValidationError):
            EvidenceItem(
                field_name="test",
                extracted_value="value",
                confidence=1.5  # Out of bounds
            )
    
    def test_extracted_value_any_type(self):
        """Should accept any type for extracted_value."""
        # String
        item1 = EvidenceItem(field_name="title", extracted_value="Test Title")
        assert item1.extracted_value == "Test Title"
        
        # Number
        item2 = EvidenceItem(field_name="year", extracted_value=2024)
        assert item2.extracted_value == 2024
        
        # List
        item3 = EvidenceItem(field_name="authors", extracted_value=["Smith", "Jones"])
        assert item3.extracted_value == ["Smith", "Jones"]
        
        # Dict
        item4 = EvidenceItem(field_name="metadata", extracted_value={"key": "value"})
        assert item4.extracted_value == {"key": "value"}


class TestExtractionWithEvidence:
    """Test ExtractionWithEvidence model."""
    
    def test_extraction_with_evidence_minimal(self):
        """Should create ExtractionWithEvidence with minimal fields."""
        result = ExtractionWithEvidence(
            data={"doi": "10.1234/test"}
        )
        assert result.data == {"doi": "10.1234/test"}
        assert result.evidence == []  # Default
        assert result.extraction_metadata == {}  # Default
    
    def test_extraction_with_evidence_full(self):
        """Should create ExtractionWithEvidence with all fields."""
        evidence_item = EvidenceItem(
            field_name="doi",
            extracted_value="10.1234/test",
            exact_quote="DOI: 10.1234/test"
        )
        
        result = ExtractionWithEvidence(
            data={"doi": "10.1234/test", "year": 2024},
            evidence=[evidence_item],
            extraction_metadata={"model": "gpt-4", "tokens": 1000}
        )
        
        assert result.data["doi"] == "10.1234/test"
        assert result.data["year"] == 2024
        assert len(result.evidence) == 1
        assert result.evidence[0].field_name == "doi"
        assert result.extraction_metadata["model"] == "gpt-4"
    
    def test_extraction_with_multiple_evidence(self):
        """Should handle multiple evidence items."""
        evidence1 = EvidenceItem(field_name="doi", extracted_value="10.1234/test")
        evidence2 = EvidenceItem(field_name="year", extracted_value=2024)
        
        result = ExtractionWithEvidence(
            data={"doi": "10.1234/test", "year": 2024},
            evidence=[evidence1, evidence2]
        )
        
        assert len(result.evidence) == 2
        assert result.evidence[0].field_name == "doi"
        assert result.evidence[1].field_name == "year"


class TestEvidenceResponse:
    """Test EvidenceResponse model."""
    
    def test_evidence_response_creation(self):
        """Should create EvidenceResponse with evidence list."""
        evidence_item = EvidenceItem(
            field_name="doi",
            extracted_value="10.1234/test"
        )
        
        response = EvidenceResponse(evidence=[evidence_item])
        
        assert isinstance(response.evidence, list)
        assert len(response.evidence) == 1
        assert response.evidence[0].field_name == "doi"
    
    def test_evidence_response_empty(self):
        """Should create EvidenceResponse with empty evidence."""
        response = EvidenceResponse(evidence=[])
        
        assert isinstance(response.evidence, list)
        assert len(response.evidence) == 0
    
    def test_evidence_response_multiple_items(self):
        """Should handle multiple evidence items."""
        items = [
            EvidenceItem(field_name="doi", extracted_value="10.1234/test"),
            EvidenceItem(field_name="year", extracted_value=2024),
            EvidenceItem(field_name="title", extracted_value="Test Paper")
        ]
        
        response = EvidenceResponse(evidence=items)
        
        assert len(response.evidence) == 3
        assert response.evidence[0].field_name == "doi"
        assert response.evidence[1].field_name == "year"
        assert response.evidence[2].field_name == "title"

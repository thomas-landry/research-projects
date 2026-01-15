"""
Tests for ComplexityClassifier integration into DocumentParser.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from core.parsers.manager import DocumentParser
from core.complexity_classifier import ComplexityClassifier, ComplexityLevel, ComplexityResult
from core.parsers.base import ParsedDocument, DocumentChunk

@pytest.fixture
def mock_classifier():
    with patch("core.parsers.manager.ComplexityClassifier") as MockClass:
        classifier_instance = MockClass.return_value
        yield classifier_instance

@pytest.fixture
def mock_docling():
    with patch("core.parsers.manager.DoclingParser") as MockClass:
        yield MockClass.return_value

@pytest.fixture
def mock_pymupdf():
    with patch("core.parsers.manager.PyMuPDFParser") as MockClass:
        yield MockClass.return_value

@pytest.fixture
def parser(mock_classifier, mock_docling, mock_pymupdf):
    return DocumentParser()

def test_parse_pdf_uses_pymupdf_initially(parser, mock_pymupdf, mock_classifier):
    """Test that parser starts with PyMuPDF (scanner)."""
    # Setup
    pdf_path = "test.pdf"
    with patch("pathlib.Path.exists", return_value=True), \
         patch.object(parser, "_load_cached", return_value=None), \
         patch.object(parser, "_save_to_cache"):
        parser.parse_pdf(pdf_path)
    
    # Verification
    mock_pymupdf.parse.assert_called_once()
    # Should calculate complexity
    mock_classifier.get_parser_strategy.assert_called_once()

def test_parse_pdf_switches_to_docling_for_complex(parser, mock_pymupdf, mock_docling, mock_classifier):
    """Test that parser switches to Docling if classified as complex."""
    # Setup
    pdf_path = "complex.pdf"
    
    # Mock PyMuPDF result
    simple_doc = ParsedDocument(filename="complex.pdf", chunks=[], full_text="Complex layout", metadata={})
    mock_pymupdf.parse.return_value = simple_doc
    
    # Mock Classifier result -> Recommend Docling
    mock_classifier.get_parser_strategy.return_value = {
        "primary": "docling",
        "fallback": "pdfplumber", 
        "use_ocr": True
    }
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch.object(parser, "_load_cached", return_value=None), \
         patch.object(parser, "_save_to_cache"):
        result = parser.parse_pdf(pdf_path)
        
    # Verification
    mock_pymupdf.parse.assert_called_once() # Scan
    mock_classifier.get_parser_strategy.assert_called_with(simple_doc) # Classify
    mock_docling.parse.assert_called_once() # Re-parse

def test_parse_pdf_keeps_pymupdf_for_simple(parser, mock_pymupdf, mock_docling, mock_classifier):
    """Test that parser keeps PyMuPDF result if classified as simple."""
    # Setup
    pdf_path = "simple.pdf"
    
    # Mock PyMuPDF result
    simple_doc = ParsedDocument(filename="simple.pdf", chunks=[], full_text="Simple text", metadata={})
    mock_pymupdf.parse.return_value = simple_doc
    
    # Mock Classifier result -> Recommend PyMuPDF
    mock_classifier.get_parser_strategy.return_value = {
        "primary": "pymupdf",
        "fallback": None, 
        "use_ocr": False
    }
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch.object(parser, "_load_cached", return_value=None), \
         patch.object(parser, "_save_to_cache"):
        result = parser.parse_pdf(pdf_path)
        
    # Verification
    mock_pymupdf.parse.assert_called_once() # Scan
    mock_docling.parse.assert_not_called() # No re-parse
    assert result == simple_doc

"""
Tests for DocumentParser extended functionality.

These tests verify the parser's ability to handle text and PDF files,
and verify the parse_file dispatch logic.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from core.parser import DocumentParser, ParsedDocument, DocumentChunk


@pytest.fixture
def parser():
    return DocumentParser()


def test_parse_txt_file(parser, tmp_path):
    """Test parsing a simple text file."""
    f = tmp_path / "test.txt"
    f.write_text("Paragraph 1.\n\nParagraph 2.")
    
    doc = parser.parse_file(str(f))
    
    # _simple_chunk combines text if < 1000 chars, so expected to be 1 chunk
    assert len(doc.chunks) == 1
    assert "Paragraph 1" in doc.chunks[0].text
    assert "Paragraph 2" in doc.chunks[0].text
    assert doc.filename == "test.txt"


def test_parse_txt_large_file(parser, tmp_path):
    """Test parsing a large text file that requires chunking."""
    # Create text larger than chunk_size (1000 chars)
    large_text = "This is a test paragraph. " * 100  # ~2600 chars
    f = tmp_path / "large.txt"
    f.write_text(large_text)
    
    doc = parser.parse_file(str(f))
    
    # Should have multiple chunks due to size
    assert len(doc.chunks) >= 2
    assert doc.full_text == large_text


def test_parse_file_dispatch_txt(parser, tmp_path):
    """Test that parse_file correctly dispatches .txt files."""
    txt = tmp_path / "test.txt"
    txt.write_text("Test content")
    
    # _parse_txt is now delegated to TextParser.parse
    # We can inspect if _text_parser.parse is called
    with patch.object(parser._text_parser, 'parse', wraps=parser._text_parser.parse) as mock_txt:
        doc = parser.parse_file(str(txt))
        mock_txt.assert_called_once()
        assert doc is not None


def test_parse_file_dispatch_pdf(parser, tmp_path):
    """Test that parse_file correctly dispatches .pdf files."""
    # Create a minimal valid PDF structure (will fail to parse but tests dispatch)
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b'%PDF-1.4\n')  # Minimal PDF header
    
    with patch.object(parser, 'parse_pdf', return_value=ParsedDocument(filename="test.pdf")) as mock_pdf:
        doc = parser.parse_file(str(pdf))
        mock_pdf.assert_called_once_with(str(pdf))


def test_parse_file_unsupported_extension(parser, tmp_path):
    """Test that parse_file raises error for unsupported extensions."""
    unsupported = tmp_path / "test.docx"
    unsupported.touch()
    
    with pytest.raises(ValueError, match="Unsupported file extension"):
        parser.parse_file(str(unsupported))


def test_parse_file_not_found(parser):
    """Test that parse_file raises error for non-existent files."""
    with pytest.raises(FileNotFoundError):
        parser.parse_file("/nonexistent/file.txt")


def test_parsed_document_abstract_property():
    """Test the abstract property extraction."""
    doc = ParsedDocument(
        filename="test.pdf",
        chunks=[
            DocumentChunk(text="Introduction text", section="Introduction"),
            DocumentChunk(text="This is the abstract content.", section="Abstract"),
            DocumentChunk(text="Methods text", section="Methods"),
        ]
    )
    
    assert doc.abstract == "This is the abstract content."


def test_parsed_document_methods_property():
    """Test the methods_text property extraction."""
    doc = ParsedDocument(
        filename="test.pdf",
        chunks=[
            DocumentChunk(text="Abstract text", section="Abstract"),
            DocumentChunk(text="Study design details.", section="Study Design"),
            DocumentChunk(text="Patient selection.", section="Patients and Methods"),
        ]
    )
    
    methods = doc.methods_text
    assert "Study design details" in methods
    assert "Patient selection" in methods


def test_parsed_document_results_property():
    """Test the results_text property extraction."""
    doc = ParsedDocument(
        filename="test.pdf",
        chunks=[
            DocumentChunk(text="Methods text", section="Methods"),
            DocumentChunk(text="Key findings here.", section="Results"),
            DocumentChunk(text="More findings.", section="Findings"),
        ]
    )
    
    results = doc.results_text
    assert "Key findings" in results
    assert "More findings" in results


def test_get_extraction_context():
    """Test the get_extraction_context method."""
    # Need enough text to exceed 500 char threshold (otherwise falls back to full_text)
    abstract_text = "This is the abstract with enough content to be meaningful. " * 5
    methods_text = "Our methods included detailed procedures for patient selection, data collection, and analysis. " * 5
    results_text = "Results showed significant improvements in all measured outcomes. " * 5
    
    doc = ParsedDocument(
        filename="test.pdf",
        chunks=[
            DocumentChunk(text=abstract_text, section="Abstract"),
            DocumentChunk(text=methods_text, section="Methods"),
            DocumentChunk(text=results_text, section="Results"),
        ],
        full_text="Full text fallback content"
    )
    
    context = doc.get_extraction_context(max_chars=10000)
    assert "ABSTRACT:" in context
    assert "METHODS:" in context
    assert "RESULTS:" in context

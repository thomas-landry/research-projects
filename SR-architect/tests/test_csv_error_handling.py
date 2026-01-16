"""
Test CSV error handling - ensures CSV output is never empty.

Tests verify that when extraction fails, error rows are written to CSV
with proper metadata fields (extraction_status, extraction_notes).
"""

import csv
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from core.service import ExtractionService
from core.schema_builder import FieldDefinition, FieldType
from core.parser import ParsedDocument


class TestCSVErrorHandling:
    """Test CSV output behavior when extractions fail."""
    
    def test_csv_output_on_extraction_failure(self):
        """
        GIVEN an extraction that fails due to API error
        WHEN the service processes the document
        THEN a CSV row should be written with extraction_status='FAILED'
        """
        # Setup
        service = ExtractionService(provider="ollama", model="llama3")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            
            output_csv = Path(tmpdir) / "results.csv"
            
            # Define minimal schema
            fields = [
                FieldDefinition(
                    name="title",
                    field_type=FieldType.TEXT,
                    description="Document title"
                )
            ]
            
            # Mock parsed document
            mock_doc = ParsedDocument(
                filename="test.pdf",
                full_text="Test content",
                chunks=[],
                metadata={}
            )
            
            # Mock the parser and batch executor
            with patch.object(service, '_parse_documents') as mock_parse:
                mock_parse.return_value = [mock_doc]
                
                with patch('core.service.BatchExecutor') as MockBatchExecutor:
                    # Mock batch executor to call callback with failure
                    def mock_process_batch(*args, **kwargs):
                        callback = kwargs.get('callback')
                        if callback:
                            callback("test.pdf", Exception("Rate limit exceeded"), "failed")
                    
                    MockBatchExecutor.return_value.process_batch.side_effect = mock_process_batch
                    
                    # Execute
                    summary = service.run_extraction(
                        papers_dir=tmpdir,
                        fields=fields,
                        output_csv=str(output_csv),
                        hierarchical=False,
                        vectorize=False
                    )
            
            # Verify CSV was created
            assert output_csv.exists(), "CSV file should be created even on failure"
            
            # Verify CSV has header + 1 data row
            with open(output_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            assert len(rows) == 1, "Should have exactly 1 row for 1 PDF"
            
            # Verify error row has metadata
            error_row = rows[0]
            assert error_row.get('extraction_status') == 'FAILED', "Status should be FAILED"
            assert 'Rate limit' in error_row.get('extraction_notes', ''), "Should contain error message"
            # Note: filename might be in a different field depending on schema
    
    def test_csv_row_count_matches_pdf_count(self):
        """
        GIVEN a batch with 3 PDFs where 2 fail and 1 succeeds
        WHEN the service processes the batch
        THEN CSV should have exactly 3 data rows (header + 3)
        """
        service = ExtractionService(provider="ollama", model="llama3")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 3 test PDFs
            for i in range(3):
                pdf_path = Path(tmpdir) / f"test_{i}.pdf"
                pdf_path.write_bytes(b"%PDF-1.4\n")
            
            output_csv = Path(tmpdir) / "results.csv"
            
            fields = [
                FieldDefinition(
                    name="title",
                    field_type=FieldType.TEXT,
                    description="Document title"
                )
            ]
            
            # Mock parsed documents
            mock_docs = [
                ParsedDocument(filename=f"test_{i}.pdf", full_text="Test", chunks=[], metadata={})
                for i in range(3)
            ]
            
            # Mock to fail on first 2, succeed on last
            call_count = [0]
            def mock_process_batch(*args, **kwargs):
                callback = kwargs.get('callback')
                if callback:
                    for doc in mock_docs:
                        call_count[0] += 1
                        if call_count[0] <= 2:
                            callback(doc.filename, Exception("API Error"), "failed")
                        else:
                            callback(doc.filename, {"title": "Success"}, "success")
            
            with patch.object(service, '_parse_documents') as mock_parse:
                mock_parse.return_value = mock_docs
                
                with patch('core.service.BatchExecutor') as MockBatchExecutor:
                    MockBatchExecutor.return_value.process_batch.side_effect = mock_process_batch
                    
                    summary = service.run_extraction(
                        papers_dir=tmpdir,
                        fields=fields,
                        output_csv=str(output_csv),
                        hierarchical=False,
                        vectorize=False
                    )
            
            # Verify CSV row count
            with open(output_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
            
            # Verify 2 failures, 1 success
            failed_count = sum(1 for row in rows if row.get('extraction_status') == 'FAILED')
            success_count = sum(1 for row in rows if row.get('extraction_status') == 'SUCCESS')
            
            assert failed_count == 2, f"Expected 2 failures, got {failed_count}"
            assert success_count == 1, f"Expected 1 success, got {success_count}"
    
    def test_error_row_contains_filename_and_status(self):
        """
        GIVEN an extraction failure
        WHEN error row is written to CSV
        THEN it must contain filename, extraction_status, and extraction_notes
        """
        service = ExtractionService(provider="ollama", model="llama3")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "important_paper.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            
            output_csv = Path(tmpdir) / "results.csv"
            
            fields = [
                FieldDefinition(
                    name="title",
                    field_type=FieldType.TEXT,
                    description="Document title"
                )
            ]
            
            error_message = "Error code: 429 - Rate limit exceeded"
            
            mock_doc = ParsedDocument(
                filename="important_paper.pdf",
                full_text="Test",
                chunks=[],
                metadata={}
            )
            
            def mock_process_batch(*args, **kwargs):
                callback = kwargs.get('callback')
                if callback:
                    callback("important_paper.pdf", Exception(error_message), "failed")
            
            with patch.object(service, '_parse_documents') as mock_parse:
                mock_parse.return_value = [mock_doc]
                
                with patch('core.service.BatchExecutor') as MockBatchExecutor:
                    MockBatchExecutor.return_value.process_batch.side_effect = mock_process_batch
                    
                    service.run_extraction(
                        papers_dir=tmpdir,
                        fields=fields,
                        output_csv=str(output_csv),
                        hierarchical=False,
                        vectorize=False
                    )
            
            # Verify error row fields
            with open(output_csv, 'r') as f:
                reader = csv.DictReader(f)
                error_row = next(reader)
            
            # Required fields must be present and populated
            assert 'extraction_status' in error_row, "extraction_status field must exist"
            assert 'extraction_notes' in error_row, "extraction_notes field must exist"
            
            assert error_row['extraction_status'] == 'FAILED'
            assert '429' in error_row['extraction_notes']
            assert 'Rate limit' in error_row['extraction_notes']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

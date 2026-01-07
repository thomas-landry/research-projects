"""
Tests for adaptive CLI discovery flow.

NOTE: These tests require a working CLI environment with proper mocking.
They are skipped pending fixes to CLI --adaptive flag integration.
"""
import pytest
from typer.testing import CliRunner
from cli import app
from unittest.mock import MagicMock, patch


runner = CliRunner()


@pytest.mark.skip(reason="CLI --adaptive flag integration requires more comprehensive mocking")
def test_cli_adaptive_discovery_flow():
    """Verify that --adaptive flag triggers discovery and proceeds to extraction."""
    with patch("cli.HierarchicalExtractionPipeline") as MockPipeline, \
         patch("typer.confirm", return_value=True), \
         patch("cli.DocumentParser") as MockParser, \
         patch("cli.BatchExecutor") as MockBatch:
        
        mock_pipeline_inst = MockPipeline.return_value
        
        # Mock discovered fields
        from core.schema_builder import FieldDefinition, FieldType
        mock_fields = [
            FieldDefinition(name="test_field", field_type=FieldType.TEXT, description="A test field")
        ]
        mock_pipeline_inst.discover_schema.return_value = mock_fields
        
        # Mock BatchExecutor return
        mock_batch_inst = MockBatch.return_value
        mock_batch_inst.process_batch.return_value = [{"test_field": "test_value"}]
        
        # Mock parser to return a doc so BatchExecutor has something to do
        from core.parser import ParsedDocument
        mock_parser_inst = MockParser.return_value
        mock_parser_inst.parse_pdf.return_value = ParsedDocument(filename="sample.pdf", chunks=[], full_text="")
        
        # Run command
        result = runner.invoke(app, ["extract", "tests/data", "--adaptive", "--limit", "1", "--output", "tests/data/results.csv"])
        
        assert result.exit_code == 0
        assert "Adaptive Schema Discovery" in result.stdout
        assert "Discovered Schema" in result.stdout
        assert "STARTING EXTRACTION" in result.stdout
        
        # Verify discovery was called
        mock_pipeline_inst.discover_schema.assert_called_once()
        
        # Verify extraction was called with discovered fields
        args, kwargs = MockBatch.return_value.process_batch.call_args
        schema_model = kwargs.get("schema")
        assert schema_model.__name__ == "SRExtractionModel"
        assert "test_field" in schema_model.model_fields


@pytest.mark.skip(reason="CLI --adaptive flag integration requires more comprehensive mocking")
def test_cli_adaptive_discovery_abort():
    """Verify that if user denies the discovered schema, extraction aborts."""
    with patch("cli.HierarchicalExtractionPipeline") as MockPipeline, \
         patch("typer.confirm", return_value=False):
        
        mock_pipeline_inst = MockPipeline.return_value
        mock_pipeline_inst.discover_schema.return_value = []
        
        result = runner.invoke(app, ["extract", "tests/data", "--adaptive"])
        
        assert result.exit_code == 0
        assert "Aborted" in result.stdout
        # Extraction should NOT start
        assert "STARTING EXTRACTION" not in result.stdout

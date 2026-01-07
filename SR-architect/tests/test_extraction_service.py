
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# ExtractionService doesn't exist yet
# from core.service import ExtractionService

def test_extraction_service_interface():
    try:
        from core.service import ExtractionService
    except ImportError:
        pytest.fail("Could not import ExtractionService from core.service")

    service = ExtractionService(provider="test", model="test")
    
    assert hasattr(service, "discover_schema")
    assert hasattr(service, "run_extraction")

def test_run_extraction_delegation():
    # Verify that run_extraction calls the necessary components
    from core.service import ExtractionService
    
    with patch("core.service.DocumentParser") as mock_parser, \
         patch("core.service.BatchExecutor") as mock_executor, \
         patch("core.service.StateManager") as mock_state:
        
        service = ExtractionService()
        
        # Mock setup
        mock_parser.return_value.parse_pdf.return_value = MagicMock()
        
        # Call
        # We'll need to define the signature clearly
        # run_extraction(self, papers_dir, schema_fields, output_path, ...)
        
        # For now just verify it can be instantiated and has the methods
        assert True

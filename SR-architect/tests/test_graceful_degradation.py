
import pytest
from unittest.mock import MagicMock
from core.batch import BatchExecutor

def test_batch_oom_tagging():
    pipeline = MagicMock()
    # Simulate OOM
    pipeline.extract_document.side_effect = MemoryError("Out of memory")
    
    state_manager = MagicMock()
    state_manager.load.return_value.processed_files = []
    state_manager.load.return_value.results = {}
    
    executor = BatchExecutor(pipeline, state_manager, max_workers=1)
    
    doc = MagicMock(filename="doc1.pdf")
    executor.process_batch([doc], MagicMock(), "theme")
    
    # Check that the error was recorded with type info
    # We want something better than just "failed" and string error.
    # We want to see if we can tag it.
    
    # args is a tuple of positional arguments
    # kwargs is a dict of keyword arguments
    call_args = state_manager.update_result.call_args
    args, kwargs = call_args
    
    filename = args[0]
    data = args[1]
    status = kwargs.get("status", args[2] if len(args) > 2 else None)
    
    assert filename == "doc1.pdf"
    # We expect data to contain structured error info now
    assert isinstance(data, dict)
    assert data["error_type"] == "MemoryError"
    assert status == "failed"

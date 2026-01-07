import pytest
from unittest.mock import MagicMock
from core.batch_processor import BatchExecutor
from core.state_manager import StateManager, PipelineCheckpoint
from core.parser import ParsedDocument
from pydantic import BaseModel

class MockSchema(BaseModel):
    field: str

@pytest.fixture
def mock_pipeline():
    p = MagicMock()
    # Mock extract_document to return a dict or object with model_dump
    result = MagicMock()
    result.model_dump.return_value = {"field": "value"}
    p.extract_document.return_value = result
    return p

@pytest.fixture
def mock_state_manager():
    sm = MagicMock(spec=StateManager)
    # Default state
    sm.load.return_value = PipelineCheckpoint()
    return sm

def test_batch_execution(mock_pipeline, mock_state_manager):
    executor = BatchExecutor(mock_pipeline, mock_state_manager, max_workers=2)
    
    docs = [
        ParsedDocument(filename="doc1.pdf", chunks=[], full_text=""),
        ParsedDocument(filename="doc2.pdf", chunks=[], full_text="")
    ]
    
    results = executor.process_batch(docs, MockSchema, "theme")
    
    assert mock_pipeline.extract_document.call_count == 2
    # Verify state updates
    assert mock_state_manager.update_result.call_count == 2
    # Verify final load called
    assert mock_state_manager.load.call_count >= 2  # initial + final

def test_resume_logic(mock_pipeline, mock_state_manager):
    # Setup state with doc1 done
    state = PipelineCheckpoint()
    state.processed_files.add("doc1.pdf")
    state.results["doc1.pdf"] = {"existing": "data"}
    mock_state_manager.load.return_value = state
    
    executor = BatchExecutor(mock_pipeline, mock_state_manager)
    
    docs = [
        ParsedDocument(filename="doc1.pdf", chunks=[], full_text=""),
        ParsedDocument(filename="doc2.pdf", chunks=[], full_text="")
    ]
    
    results = executor.process_batch(docs, MockSchema, "theme", resume=True)
    
    # only doc2 processed
    assert mock_pipeline.extract_document.call_count == 1
    args, _ = mock_pipeline.extract_document.call_args
    assert args[0].filename == "doc2.pdf"

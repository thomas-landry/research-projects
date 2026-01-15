import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.batch import BatchExecutor

@pytest.mark.asyncio
async def test_batch_semaphore_safety():
    """Verify BatchExecutor handles zero-worker recommendation safely."""
    
    # Mock dependencies
    pipeline = MagicMock()
    pipeline.extract_document_async = AsyncMock(return_value={"data": "ok"})
    
    state_manager = MagicMock()
    state_manager.load.return_value = MagicMock(processed_files=set(), results={})
    state_manager.update_result = MagicMock() # Mock the update
    state_manager.save_async = AsyncMock() # Required for new async save
    
    # Mock Resource Manager returning 0 workers
    resource_manager = MagicMock()
    resource_manager.get_recommended_workers.return_value = 0
    
    executor = BatchExecutor(
        pipeline=pipeline, 
        state_manager=state_manager, 
        max_workers=4,
        resource_manager=resource_manager
    )
    
    # Dummy doc
    doc = MagicMock()
    doc.filename = "test.pdf"
    
    # Run
    # This should NOT hang. If semaphore was 0, it would hang.
    results = await executor.process_batch_async([doc], schema=None, theme="test")
    
    # results will be empty because state_manager.load() mock returns empty dict
    # But if we reached here, we didn't deadlock.
    
    # Verify execution happened
    assert pipeline.extract_document_async.called
    state_manager.update_result.assert_called()

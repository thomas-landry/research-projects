
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from core.batch import BatchExecutor

def test_batch_executor_accepts_resource_manager():
    pipeline = MagicMock()
    state_manager = MagicMock()
    rm = MagicMock()
    
    # This should NOT fail now
    try:
        BatchExecutor(pipeline, state_manager, max_workers=4, resource_manager=rm)
    except TypeError:
        pytest.fail("BatchExecutor does not accept resource_manager argument")

def test_batch_throttling_logic():
    pipeline = MagicMock()
    state_manager = MagicMock()
    state_manager.load.return_value.processed_files = []
    state_manager.load.return_value.results = {}
    rm = MagicMock()
    rm.get_recommended_workers.return_value = 2
    
    executor = BatchExecutor(pipeline, state_manager, max_workers=4, resource_manager=rm)
    
    # Mock asyncio.Semaphore to verify it uses the throttled value
    with patch("asyncio.Semaphore") as mock_sem:
        # Run async method synchronously wrapper
        async def run():
            # Mock gather to avoid execution
            async def mock_gather_fn(*args, **kwargs):
                return []
                
            with patch("asyncio.gather", side_effect=mock_gather_fn):
                docs = [MagicMock(filename="doc1")]
                await executor.process_batch_async(docs, MagicMock(), "theme")
        
        asyncio.run(run())
        
        # Verify it called get_recommended_workers
        rm.get_recommended_workers.assert_called_with(4)
        # Verify Semaphore init with 2
        mock_sem.assert_called_with(2)

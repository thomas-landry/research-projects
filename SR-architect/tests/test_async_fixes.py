import pytest
import asyncio
import json
from pathlib import Path
from core.state_manager import StateManager
from core.utils import LLMCache

@pytest.mark.asyncio
async def test_state_manager_save_async(tmp_path):
    """Verify that save_async writes to disk without blocking."""
    checkpoint_path = tmp_path / "checkpoint.json"
    manager = StateManager(checkpoint_path=checkpoint_path)
    
    # Update state
    manager.update_result("test.pdf", {"data": 1}, save=False)
    
    # Verify not saved yet (if save=False worked)
    assert not checkpoint_path.exists()
    
    # Async Save
    await manager.save_async()
    
    # Verify saved
    assert checkpoint_path.exists()
    with open(checkpoint_path) as f:
        data = json.load(f)
        assert "test.pdf" in data["processed_files"]

@pytest.mark.asyncio
async def test_llm_cache_async(tmp_path):
    """Verify get_async and set_async."""
    cache = LLMCache(cache_dir=str(tmp_path))
    model = "test-model"
    messages = [{"role": "user", "content": "hello"}]
    data = {"response": "world"}
    
    # Set Async
    await cache.set_async(model, messages, data)
    
    # Get Async
    result = await cache.get_async(model, messages)
    assert result == data
    
    # Verify file exists
    assert list(tmp_path.glob("*.json"))

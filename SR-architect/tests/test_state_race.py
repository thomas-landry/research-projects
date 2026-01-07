import pytest
import asyncio
import threading
from core.state_manager import StateManager
from pydantic import BaseModel

class MockResult(BaseModel):
    id: int
    data: str

@pytest.mark.asyncio
async def test_state_race_condition(tmp_path):
    """
    Verify if updating state while saving in background causes RuntimeError (dict changed size).
    """
    checkpoint_path = tmp_path / "race_checkpoint.json"
    manager = StateManager(checkpoint_path=checkpoint_path)
    
    # Pre-fill state to make serialization take some non-zero time
    for i in range(1000):
        manager.update_result(f"pre_{i}.pdf", {"data": "x"*100}, save=False)
        
    stop_event = asyncio.Event()
    
    async def updater():
        """Continuously update state."""
        i = 0
        while not stop_event.is_set():
            manager.update_result(f"doc_{i}.pdf", {"data": "y"*100}, save=False)
            i += 1
            await asyncio.sleep(0.0001) # Yield slightly
            
    async def saver():
        """Continuously save state async."""
        while not stop_event.is_set():
            try:
                await manager.save_async()
            except RuntimeError as e:
                if "dictionary changed size" in str(e):
                    return "CRASHED"
            await asyncio.sleep(0.001)
            
    task_update = asyncio.create_task(updater())
    
    # Run saver for a bit
    crashed = False
    for _ in range(50): # Try 50 saves
        try:
             await manager.save_async()
        except Exception as e:
             if "dictionary changed size" in str(e):
                 crashed = True
                 break
        await asyncio.sleep(0.01)
    
    stop_event.set()
    await task_update
    
    if crashed:
        pytest.fail("StateManager crashed due to race condition: dictionary changed size during iteration")

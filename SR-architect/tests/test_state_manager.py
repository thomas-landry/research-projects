import pytest
from pathlib import Path
from datetime import datetime
from core.state_manager import StateManager, PipelineCheckpoint

@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "test_state.json"

@pytest.fixture
def manager(state_file):
    return StateManager(state_file)

def test_initial_state(manager):
    state = manager.load()
    assert isinstance(state, PipelineCheckpoint)
    assert len(state.processed_files) == 0
    assert len(state.results) == 0

def test_save_and_load(manager):
    # Modify state
    manager.state.processed_files.add("doc1.pdf")
    manager.state.results["doc1.pdf"] = {"data": "test"}
    manager.save()
    
    # Reload in new manager
    new_manager = StateManager(manager.checkpoint_path)
    loaded = new_manager.load()
    
    assert "doc1.pdf" in loaded.processed_files
    assert loaded.results["doc1.pdf"]["data"] == "test"

def test_atomic_write(manager):
    # Verify temp file creation during save (though hard to catch race condition in test)
    manager.save()
    assert manager.checkpoint_path.exists()
    assert not manager.checkpoint_path.with_suffix(".tmp").exists()

def test_corrupted_file_backup(state_file, manager):
    # Write garbage
    with open(state_file, "w") as f:
        f.write("{garbage json")
    
    # Load should backup and start fresh
    state = manager.load()
    assert len(state.processed_files) == 0
    
    # Verify backup exists
    # Note: with_suffix replaces the last extension (.json), so it becomes .bak.timestamp
    backups = list(state_file.parent.glob("test_state.bak.*"))
    assert len(backups) == 1

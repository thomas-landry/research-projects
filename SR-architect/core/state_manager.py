import json
import fcntl
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from pydantic import BaseModel, Field, model_validator

from core import utils

logger = utils.get_logger(__name__)

class PipelineCheckpoint(BaseModel):
    """
    Pydantic model for pipeline state checkpointing.
    Replaces unsafe pickle serialization with JSON.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    processed_files: Set[str] = Field(default_factory=set)
    failed_files: Set[str] = Field(default_factory=set)
    results: Dict[str, Any] = Field(default_factory=dict)  # filename -> result dict
    extraction_stats: Dict[str, int] = Field(default_factory=lambda: {
        "total": 0, "success": 0, "failed": 0
    })

    @model_validator(mode='before')
    @classmethod
    def convert_sets(cls, data: Any) -> Any:
        # Handle JSON loading where sets are lists
        if isinstance(data, dict):
            if 'processed_files' in data and isinstance(data['processed_files'], list):
                data['processed_files'] = set(data['processed_files'])
            if 'failed_files' in data and isinstance(data['failed_files'], list):
                data['failed_files'] = set(data['failed_files'])
        return data

    def model_dump_json(self, **kwargs) -> str:
        # Custom dump to handle set serialization
        data = self.model_dump()
        data['processed_files'] = list(data['processed_files'])
        data['failed_files'] = list(data['failed_files'])
        # Handle datetime serialization
        data['timestamp'] = data['timestamp'].isoformat()
        return json.dumps(data, **kwargs)

class StateManager:
    """
    Manages loading and saving of pipeline state using safe JSON serialization.
    Implements atomic writes and file locking for safety.
    """
    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = Path(checkpoint_path)
        self.state = PipelineCheckpoint()

    def load(self) -> PipelineCheckpoint:
        """Load state from JSON checkpoint file."""
        if not self.checkpoint_path.exists():
            logger.info(f"No checkpoint found at {self.checkpoint_path}, starting fresh.")
            return self.state

        try:
            with open(self.checkpoint_path, 'r') as f:
                data = json.load(f)
            self.state = PipelineCheckpoint(**data)
            logger.info(f"Loaded checkpoint with {len(self.state.processed_files)} processed files.")
            return self.state
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load checkpoint: {e}. Starting fresh.")
            # Backup corrupted checkpoint
            backup_path = self.checkpoint_path.with_suffix(f".bak.{int(datetime.now().timestamp())}")
            if self.checkpoint_path.exists():
                logger.warning(f"Backing up corrupted checkpoint to {backup_path}")
                self.checkpoint_path.rename(backup_path)
            return self.state

    def save(self) -> None:
        """
        Atomic save of state to JSON file.
        Uses a temporary file + rename to ensure data integrity.
        """
        temp_path = self.checkpoint_path.with_suffix('.tmp')
        try:
            # Serialize manually to handle Sets and Datetime generally
            json_str = self.state.model_dump_json(indent=2)
            
            with open(temp_path, 'w') as f:
                # File locking (Unix only)
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json_str)
                f.flush()
                # fsync to force write to disk
                import os
                os.fsync(f.fileno())
                fcntl.flock(f, fcntl.LOCK_UN)
            
            # Atomic rename
            temp_path.replace(self.checkpoint_path)
            logger.debug(f"Saved checkpoint to {self.checkpoint_path}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            if temp_path.exists():
                temp_path.unlink()

    async def save_async(self) -> None:
        """
        Save the current state to the checkpoint file asynchronously.
        Creates a snapshot in the main thread to avoid race conditions.
        """
        import asyncio
        loop = asyncio.get_running_loop()
        
        # Snapshot the state to avoid "dictionary changed size during iteration"
        # We rely on Pydantic's model_dump to create a dict snapshot
        # This runs in main thread (blocking for a split second) but is safe.
        state_snapshot = self.state.model_copy(deep=True)
        
        await loop.run_in_executor(None, lambda: self._save_snapshot(state_snapshot))

    def _save_snapshot(self, state_snapshot) -> None:
        """Internal method to save a specific state snapshot."""
        try:
            json_str = state_snapshot.model_dump_json(indent=2)
            
            temp_path = self.checkpoint_path.with_suffix(".tmp")
            
            with open(temp_path, 'w') as f:
                # File locking (Unix only)
                try:
                    fcntl.flock(f, fcntl.LOCK_EX)
                except (IOError, OSError):
                    pass # Windows/Non-Unix fallback
                    
                f.write(json_str)
                f.flush()
                # fsync to force write to disk
                import os
                os.fsync(f.fileno())
                
                try:
                    fcntl.flock(f, fcntl.LOCK_UN)
                except (IOError, OSError):
                    pass
            
            # Atomic rename
            temp_path.replace(self.checkpoint_path)
            
        except Exception as e:
            # We use print/fallback logger here to avoid circular dependencies if needed
            print(f"Error saving checkpoint: {e}")

    def update_result(self, filename: str, result: Dict[str, Any], status: str = "success", save: bool = True):
        """Update state with a single result."""
        if status == "success":
            self.state.processed_files.add(filename)
            self.state.results[filename] = result
            self.state.extraction_stats["success"] += 1
        else:
            self.state.failed_files.add(filename)
            self.state.extraction_stats["failed"] += 1
        
        self.state.extraction_stats["total"] += 1
        
        if save:
            self.save()

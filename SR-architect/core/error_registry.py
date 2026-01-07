"""
Error Registry for collecting and tracking bugs found during local execution.
"""
import json
import traceback
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class RegistryError:
    """A captured error instance."""
    error_type: str
    message: str
    location: str
    timestamp: str
    traceback: str
    input_snippet: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @property
    def id(self) -> str:
        """Generate a stable ID based on error type and message."""
        content = f"{self.error_type}:{self.message}:{self.location}"
        return hashlib.md5(content.encode()).hexdigest()

class ErrorRegistry:
    """
    Manages a persistent registry of errors found during execution.
    Writes to 'bugs.json' in the output directory.
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        from .config import settings
        self.registry_path = registry_path or (settings.OUTPUT_DIR / "bugs.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()
        
    def _load(self):
        """Load existing errors."""
        self.errors: Dict[str, RegistryError] = {}
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                    for err_data in data:
                        # Handle legacy formats if any, currently simple
                        self.errors[err_data["id"]] = RegistryError(
                            error_type=err_data["error_type"],
                            message=err_data["message"],
                            location=err_data["location"],
                            timestamp=err_data["timestamp"],
                            traceback=err_data["traceback"],
                            input_snippet=err_data.get("input_snippet"),
                            context=err_data.get("context")
                        )
            except Exception:
                # If corrupt, start fresh (or backup? simplistic for now)
                pass
                
    def _save(self):
        """Save errors to disk."""
        data = []
        for err in self.errors.values():
            d = asdict(err)
            d["id"] = err.id
            data.append(d)
        
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def register(self, e: Exception, location: str, input_snippet: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """
        Register a new exception.
        
        Args:
            e: The exception object
            location: Where it happened (e.g. "Extractor.extract")
            input_snippet: Partial input that caused it (optional)
            context: Additional metadata (optional)
        """
        error_type = type(e).__name__
        message = str(e)
        tb = traceback.format_exc()
        
        new_error = RegistryError(
            error_type=error_type,
            message=message,
            location=location,
            timestamp=datetime.now().isoformat(),
            traceback=tb,
            input_snippet=input_snippet,
            context=context
        )
        
        # We overwrite duplicates to update timestamp/traceback if identical
        self.errors[new_error.id] = new_error
        
        # Save non-blocking if possible
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._save)
        except RuntimeError:
            self._save()

    def get_summary(self) -> List[Dict[str, str]]:
        """Return a summary of captured errors."""
        return [
            {"id": e.id, "type": e.error_type, "message": e.message, "location": e.location}
            for e in self.errors.values()
        ]

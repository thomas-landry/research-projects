from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CacheEntry:
    """Represents a cached item."""
    key: str
    value: Any
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

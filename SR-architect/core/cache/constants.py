from pathlib import Path

# Default cache database path (relative to project root)
# Assumes this file is in core/cache/constants.py -> parent=core/cache -> parent=core -> parent=root
DEFAULT_CACHE_PATH = Path(__file__).parent.parent.parent / ".cache" / "extraction_cache.db"

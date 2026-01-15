"""
Cache Manager Shim.
DEPRECATED: Use core.cache instead.
"""
from core.cache import CacheManager, CacheEntry, DEFAULT_CACHE_PATH

__all__ = ["CacheManager", "CacheEntry", "DEFAULT_CACHE_PATH"]

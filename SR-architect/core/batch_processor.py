"""
Shim for backward compatibility.
DEPRECATED: Use core.batch instead.
"""
from core.batch import BatchExecutor, ExecutionHandler, CircuitBreaker

__all__ = ["BatchExecutor", "ExecutionHandler", "CircuitBreaker"]
"""
Execution handler for batch processing.
"""
import threading
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from core import utils
from .circuit_breaker import CircuitBreaker

logger = utils.get_logger(__name__)

class ExecutionHandler:
    """
    Shared execution logic for batch processing.
    
    Centralizes result serialization and error handling to eliminate
    duplication between sync and async execution paths.
    """
    def __init__(self, state_manager, circuit_breaker: CircuitBreaker):
        """
        Initialize the execution handler.
        
        Args:
            state_manager: StateManager instance for checkpointing
            circuit_breaker: CircuitBreaker instance for failure tracking
        """
        self.state_manager = state_manager
        self.circuit_breaker = circuit_breaker
    
    def serialize_result(self, result: Any) -> Dict[str, Any]:
        """
        Serialize extraction result to dictionary.
        
        Pure function with no side effects - reusable in sync/async paths.
        
        Args:
            result: Extraction result (PipelineResult, dict, or object)
            
        Returns:
            Serialized result as dictionary
        """
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        elif hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, dict):
            return result
        return result.__dict__
    
    def handle_success(
        self,
        filename: str,
        serialized: Dict[str, Any],
        callback: Optional[Callable[[str, Any, str], None]] = None,
        save: bool = True
    ) -> tuple:
        """
        Handle successful extraction.
        
        Args:
            filename: Document filename
            serialized: Serialized extraction result
            callback: Optional progress callback
            save: Whether to save state immediately
            
        Returns:
            Tuple of (filename, serialized_result, status)
        """
        self.state_manager.update_result(filename, serialized, status="success", save=save)
        self.circuit_breaker.record_success()
        logger.info(f"✓ Completed {filename}")
        if callback:
            callback(filename, serialized, "success")
        return (filename, serialized, "success")
    
    def handle_memory_error(
        self,
        filename: str,
        callback: Optional[Callable[[str, Any, str], None]] = None,
        save: bool = True
    ) -> tuple:
        """
        Handle memory error during extraction.
        
        Args:
            filename: Document filename
            callback: Optional progress callback
            save: Whether to save state immediately
            
        Returns:
            Tuple of (filename, error_payload, status)
        """
        logger.error(f"OOM processing {filename}")
        self.circuit_breaker.record_failure()
        error_payload = {"error": "Out of memory", "error_type": "MemoryError"}
        self.state_manager.update_result(filename, error_payload, status="failed", save=save)
        if callback:
            callback(filename, error_payload, "failed")
        return (filename, error_payload, "failed")
    
    def handle_general_error(
        self,
        filename: str,
        error: Exception,
        callback: Optional[Callable[[str, Any, str], None]] = None,
        save: bool = True,
        register_error: bool = False
    ) -> tuple:
        """
        Handle general extraction error.
        
        Args:
            filename: Document filename
            error: Exception that occurred
            callback: Optional progress callback
            save: Whether to save state immediately
            register_error: Whether to register error in ErrorRegistry
            
        Returns:
            Tuple of (filename, error_payload, status)
        """
        logger.error(f"Error processing {filename}: {error}", exc_info=True)
        self.circuit_breaker.record_failure()
        
        if register_error:
            from core.error_registry import ErrorRegistry
            ErrorRegistry().register(
                error,
                location="BatchExecutor.process_batch_async",
                context={"filename": filename}
            )
        
        error_payload = {"error": str(error)}
        self.state_manager.update_result(filename, error_payload, status="failed", save=save)
        logger.error(f"✗ Failed {filename}")
        if callback:
            callback(filename, str(error), "failed")
        return (filename, error_payload, "failed")

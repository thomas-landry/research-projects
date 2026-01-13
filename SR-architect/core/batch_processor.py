import asyncio
import threading
from typing import List, Type, TypeVar, Optional, Callable, Dict, Any
from .parser import ParsedDocument
from .state_manager import StateManager
from core import utils
from core.constants import CIRCUIT_BREAKER_THRESHOLD
from concurrent.futures import ThreadPoolExecutor, as_completed

# Type variable for the schema
T = TypeVar("T")

logger = utils.get_logger(__name__)

class CircuitBreaker:
    """
    Circuit breaker to stop processing or switch modes after consecutive failures.
    """
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.failure_count = 0
        self.is_open = False
        self._lock = threading.Lock()
        
    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.threshold:
                self.is_open = True
            
    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.is_open = False
        
    def reset(self):
        with self._lock:
            self.failure_count = 0
            self.is_open = False

class ExecutionHandler:
    """
    Shared execution logic for batch processing.
    
    Centralizes result serialization and error handling to eliminate
    duplication between sync and async execution paths.
    """
    def __init__(self, state_manager: StateManager, circuit_breaker: CircuitBreaker):
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


class BatchExecutor:
    """
    Handles parallel execution of document extraction.
    Decoupled from the main pipeline logic.
    """
    def __init__(
        self,
        pipeline,
        state_manager: StateManager,
        max_workers: int = 4,
        resource_manager = None
    ):
        """
        Initialize the batch executor.
        
        Args:
            pipeline: The HierarchicalExtractionPipeline instance (duck-typed)
            state_manager: The StateManager instance for checkpointing
            max_workers: Number of parallel threads
            resource_manager: Optional ResourceManager for dynamic throttling
        """
        self.pipeline = pipeline
        self.state_manager = state_manager
        self.max_workers = max_workers
        self.resource_manager = resource_manager
        self.circuit_breaker = CircuitBreaker(threshold=CIRCUIT_BREAKER_THRESHOLD)
        self.handler = ExecutionHandler(state_manager, self.circuit_breaker)

    def process_batch(
        self,
        documents: List[ParsedDocument],
        schema: Type[T],
        theme: str,
        resume: bool = True,
        callback: Optional[Callable[[str, Any, str], None]] = None
    ) -> List[Any]:
        """
        Run extraction in parallel.
        
        Args:
            documents: List of docs to process
            schema: Pydantic model for extraction
            theme: Theme string
            resume: Whether to skip already processed files
            
        Returns:
            List of results (from state or fresh extraction)
        """
        # Load initial state
        state = self.state_manager.load()
        
        # Filter work
        to_process = []
        for doc in documents:
            if resume and doc.filename in state.processed_files:
                logger.info(f"Skipping {doc.filename} (already completed)")
            else:
                to_process.append(doc)
                
        if not to_process:
            logger.info("All documents already completed.")
            return list(state.results.values())
            
        # Apply throttling
        limit = self.max_workers
        if self.resource_manager:
            limit = self.resource_manager.get_recommended_workers(limit)
            
        logger.info(f"Starting parallel extraction [workers={limit}] for {len(to_process)} documents.")
        
        # Define worker function
        def _execute_single(doc: ParsedDocument):
            if self.circuit_breaker.is_open:
                return (doc.filename, "Circuit breaker open", "skipped")
                
            try:
                result = self.pipeline.extract_document(doc, schema, theme)
                serialized = self.handler.serialize_result(result)
                return self.handler.handle_success(doc.filename, serialized, callback)
            except MemoryError:
                return self.handler.handle_memory_error(doc.filename, callback)
            except Exception as e:
                return self.handler.handle_general_error(doc.filename, e, callback)

        # Execute
        with ThreadPoolExecutor(max_workers=limit) as executor:
            future_to_doc = {
                executor.submit(_execute_single, doc): doc 
                for doc in to_process
            }
            
            try:
                for future in as_completed(future_to_doc):
                    filename, extraction_result, extraction_status = future.result()
                    
                    if extraction_status == "skipped":
                        logger.warning(f"Skipped {filename}: {extraction_result}")
                    # Note: Success and error handling already done in _execute_single via handler
                        
            except KeyboardInterrupt:
                logger.warning("Batch processing interrupted by user. Shutting down workers...")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        # Reload state to get full results set (including previously processed)
        final_state = self.state_manager.load()
        return list(final_state.results.values())

    async def process_batch_async(
        self,
        documents: List[ParsedDocument],
        schema: Type[T],
        theme: str,
        resume: bool = True,
        callback: Optional[Callable[[str, Any, str], None]] = None,
        concurrency_limit: Optional[int] = None
    ) -> List[Any]:
        """
        Run extraction in parallel using asyncio.
        
        Args:
            documents: List of docs to process
            schema: Pydantic model for extraction
            theme: Theme string
            resume: Whether to skip already processed files
            callback: Progress callback
            concurrency_limit: Max concurrent tasks (defaults to self.max_workers)
            
        Returns:
            List of results
        """
        state = self.state_manager.load()
        to_process = []
        for doc in documents:
            if resume and doc.filename in state.processed_files:
                logger.info(f"Skipping {doc.filename} (already completed)")
            else:
                to_process.append(doc)
                
        if not to_process:
            logger.info("All documents already completed.")
            return list(state.results.values())
            
        effective_limit = concurrency_limit or self.max_workers
        
        # Apply throttling if RM is present
        if self.resource_manager:
            recommended = self.resource_manager.get_recommended_workers(effective_limit)
            if recommended < effective_limit:
                logger.info(f"Throttling concurrency from {effective_limit} to {recommended} based on system resources.")
                effective_limit = max(1, recommended)
                
        logger.info(f"Starting async parallel extraction [concurrency={effective_limit}] for {len(to_process)} documents.")
        
        semaphore = asyncio.Semaphore(effective_limit)

        async def _execute_single_async(doc: ParsedDocument):
            if self.circuit_breaker.is_open:
                logger.warning(f"Circuit breaker open - skipping {doc.filename}")
                return None

            async with semaphore:
                try:
                    result = await self.pipeline.extract_document_async(doc, schema, theme)
                    serialized = self.handler.serialize_result(result)
                    self.handler.handle_success(doc.filename, serialized, callback, save=False)
                    await self.state_manager.save_async()
                    return result
                except MemoryError:
                    self.handler.handle_memory_error(doc.filename, callback, save=False)
                    await self.state_manager.save_async()
                    return None
                except Exception as e:
                    self.handler.handle_general_error(
                        doc.filename, e, callback, save=False, register_error=True
                    )
                    await self.state_manager.save_async()
                    return None

        # Execute all tasks
        tasks = [_execute_single_async(doc) for doc in to_process]
        await asyncio.gather(*tasks)

        # Reload state to get full results set
        final_state = self.state_manager.load()
        return list(final_state.results.values())
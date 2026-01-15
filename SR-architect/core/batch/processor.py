"""
Batch processor implementation.
"""
import asyncio
from typing import List, Type, TypeVar, Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import utils
from core.parser import ParsedDocument
from core.state_manager import StateManager
from core.constants import CIRCUIT_BREAKER_THRESHOLD

from .circuit_breaker import CircuitBreaker
from .handler import ExecutionHandler

logger = utils.get_logger(__name__)

# Type variable for the schema
T = TypeVar("T")


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

    def _filter_work_items(self, documents: List[ParsedDocument], resume: bool) -> List[ParsedDocument]:
        """
        Filter documents to process based on state.
        
        Args:
            documents: List of all documents
            resume: Whether to skip processed files
            
        Returns:
            List of documents needing processing
        """
        if not resume:
            return list(documents)
            
        state = self.state_manager.load()
        to_process = []
        
        for doc in documents:
            if doc.filename in state.processed_files:
                logger.debug(f"Skipping {doc.filename} (already completed)")
            else:
                to_process.append(doc)
                
        return to_process
        
    def _execute_single(self, doc: ParsedDocument, schema: Type[T], theme: str, callback: Optional[Callable]):
        """Execute extraction for a single document (sync worker)."""
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
        # Load initial state explicitly to ensure we have latest before filtering
        # self.state_manager.load() is called inside _filter_work_items too if needed
        # But let's rely on _filter_work_items
        
        to_process = self._filter_work_items(documents, resume)
                
        if not to_process:
            logger.info("All documents already completed.")
            final_state = self.state_manager.load()
            return list(final_state.results.values())
            
        # Apply throttling
        limit = self.max_workers
        if self.resource_manager:
            limit = self.resource_manager.get_recommended_workers(limit)
            
        logger.info(f"Starting parallel extraction [workers={limit}] for {len(to_process)} documents.")
        
        # Execute
        with ThreadPoolExecutor(max_workers=limit) as executor:
            future_to_doc = {
                executor.submit(self._execute_single, doc, schema, theme, callback): doc 
                for doc in to_process
            }
            
            try:
                for future in as_completed(future_to_doc):
                    filename, extraction_result, extraction_status = future.result()
                    
                    if extraction_status == "skipped":
                        logger.warning(f"Skipped {filename}: {extraction_result}")
                        
            except KeyboardInterrupt:
                logger.warning("Batch processing interrupted by user. Shutting down workers...")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        # Reload state to get full results set (including previously processed)
        final_state = self.state_manager.load()
        return list(final_state.results.values())

    async def _execute_single_async(self, doc: ParsedDocument, schema: Type[T], theme: str, callback: Optional[Callable], semaphore: asyncio.Semaphore):
        """Execute extraction for a single document (async worker)."""
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
        to_process = self._filter_work_items(documents, resume)
                
        if not to_process:
            logger.info("All documents already completed.")
            final_state = self.state_manager.load()
            return list(final_state.results.values())
            
        effective_limit = concurrency_limit or self.max_workers
        
        # Apply throttling if RM is present
        if self.resource_manager:
            recommended = self.resource_manager.get_recommended_workers(effective_limit)
            if recommended < effective_limit:
                logger.info(f"Throttling concurrency from {effective_limit} to {recommended} based on system resources.")
                effective_limit = max(1, recommended)
                
        logger.info(f"Starting async parallel extraction [concurrency={effective_limit}] for {len(to_process)} documents.")
        
        semaphore = asyncio.Semaphore(effective_limit)
        
        # Execute all tasks
        tasks = [
            self._execute_single_async(doc, schema, theme, callback, semaphore) 
            for doc in to_process
        ]
        await asyncio.gather(*tasks)

        # Reload state to get full results set
        final_state = self.state_manager.load()
        return list(final_state.results.values())

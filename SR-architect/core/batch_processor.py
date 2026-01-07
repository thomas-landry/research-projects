import asyncio
from typing import List, Type, TypeVar, Optional, Callable, Dict, Any
from .parser import ParsedDocument
from .state_manager import StateManager
from core import utils
from concurrent.futures import ThreadPoolExecutor, as_completed

# Type variable for the schema
T = TypeVar("T")

logger = utils.get_logger(__name__)

class BatchExecutor:
    """
    Handles parallel execution of document extraction.
    Decoupled from the main pipeline logic.
    """
    def __init__(
        self,
        pipeline,
        state_manager: StateManager,
        max_workers: int = 4
    ):
        """
        Initialize the batch executor.
        
        Args:
            pipeline: The HierarchicalExtractionPipeline instance (duck-typed)
            state_manager: The StateManager instance for checkpointing
            max_workers: Number of parallel threads
        """
        self.pipeline = pipeline
        self.state_manager = state_manager
        self.max_workers = max_workers

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
            
        logger.info(f"Starting parallel extraction [workers={self.max_workers}] for {len(to_process)} documents.")
        
        # Define worker function
        def _execute_single(doc: ParsedDocument):
            try:
                # Call the pipeline's single-document extract method
                # Note: Assuming pipeline is thread-safe or stateless enough
                result = self.pipeline.extract_document(doc, schema, theme)
                return (doc.filename, result, "success")
            except Exception as e:
                logger.error(f"Error processing {doc.filename}: {e}", exc_info=True)
                return (doc.filename, str(e), "failed")

        # Execute
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_doc = {
                executor.submit(_execute_single, doc): doc 
                for doc in to_process
            }
            
            try:
                for future in as_completed(future_to_doc):
                    filename, data, status = future.result()
                    
                    if status == "success":
                        # Convert pipeline result to dict for storage if needed, 
                        # or store the object if StateManager handles it. 
                        # Assuming PipelineResult is pydantic or serializable.
                        # For now, we assume PipelineResult has a model_dump or dict method, 
                        # or we store the result.final_data
                        
                        # Use model_dump if available (Pydantic V2) or dict()
                        serialized = data.model_dump() if hasattr(data, 'model_dump') else data.__dict__
                        
                        self.state_manager.update_result(filename, serialized, status="success")
                        logger.info(f"✓ Completed {filename}")
                        if callback:
                            callback(filename, serialized, "success")
                    else:
                        self.state_manager.update_result(filename, {"error": data}, status="failed")
                        logger.error(f"✗ Failed {filename}")
                        if callback:
                            callback(filename, data, "failed")
                        
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
            
        limit = concurrency_limit or self.max_workers
        logger.info(f"Starting async parallel extraction [concurrency={limit}] for {len(to_process)} documents.")
        
        semaphore = asyncio.Semaphore(limit)

        async def _execute_single_async(doc: ParsedDocument):
            async with semaphore:
                try:
                    result = await self.pipeline.extract_document_async(doc, schema, theme)
                    
                    # Process result
                    serialized = result.model_dump() if hasattr(result, 'model_dump') else result.__dict__
                    self.state_manager.update_result(doc.filename, serialized, status="success")
                    logger.info(f"✓ Completed {doc.filename}")
                    if callback:
                        callback(doc.filename, serialized, "success")
                    return result
                except Exception as e:
                    logger.error(f"Error processing {doc.filename}: {e}", exc_info=True)
                    self.state_manager.update_result(doc.filename, {"error": str(e)}, status="failed")
                    logger.error(f"✗ Failed {doc.filename}")
                    if callback:
                        callback(doc.filename, str(e), "failed")
                    return None

        # Execute all tasks
        tasks = [_execute_single_async(doc) for doc in to_process]
        await asyncio.gather(*tasks)

        # Reload state to get full results set
        final_state = self.state_manager.load()
        return list(final_state.results.values())


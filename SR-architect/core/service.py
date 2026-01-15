
import os
import csv
import asyncio
import functools
from pathlib import Path
from typing import List, Optional, Type, Dict, Any, Callable, TextIO

from .config import settings
from .parser import DocumentParser, ParsedDocument
from .pipeline import HierarchicalExtractionPipeline
from .data_types import PipelineResult
from .batch import BatchExecutor
from .state_manager import StateManager
from .token_tracker import TokenTracker
from .audit_logger import AuditLogger
from .schema_builder import build_extraction_model, FieldDefinition
from .schema_chunker import merge_extraction_results
from .utils import get_logger, setup_logging

logger = get_logger("ExtractionService")

class ExtractionService:
    """
    High-level API for running the SR-Architect extraction pipeline.
    Encapsulates all components for easy integration into CLIs, GUIs, or other scripts.
    """
    def __init__(
        self,
        provider: str = settings.LLM_PROVIDER,
        model: Optional[str] = settings.LLM_MODEL,
        token_tracker: Optional[TokenTracker] = None,
        verbose: bool = False
    ):
        self.provider = provider
        self.model = model
        self.verbose = verbose
        self.tracker = token_tracker or TokenTracker()
        self.parser = DocumentParser()
        
    def discover_schema(
        self, 
        papers_dir: str, 
        sample_size: int = 3, 
        existing_schema: Optional[List[FieldDefinition]] = None
    ) -> List[FieldDefinition]:
        """Run adaptive schema discovery on a sample of papers."""
        from agents.schema_discovery import SchemaDiscoveryAgent
        agent = SchemaDiscoveryAgent(
            provider=self.provider, 
            model=self.model,
            token_tracker=self.tracker
        )
        return agent.discover_schema(papers_dir, sample_size, existing_schema=existing_schema)

    def _setup_extraction_context(self, output_path: Path) -> tuple[AuditLogger, StateManager]:
        """Setup logging and state management."""
        audit_log_dir = output_path.parent / "logs"
        audit_logger = AuditLogger(log_dir=str(audit_log_dir))
        checkpoint_path = output_path.parent / "extraction_checkpoint.json"
        state_manager = StateManager(checkpoint_path)
        return audit_logger, state_manager

    def _build_extraction_model(self, fields: List[FieldDefinition]) -> tuple[Type[Any], List[str]]:
        """Build Pydantic model for extraction."""
        ExtractionModel = build_extraction_model(fields, "SRExtractionModel")
        fieldnames = list(ExtractionModel.model_fields.keys())
        return ExtractionModel, fieldnames

    def _load_papers(self, papers_dir: str, limit: Optional[int] = None) -> List[Path]:
        """Load and filter PDF files."""
        papers_path = Path(papers_dir)
        pdf_files = list(papers_path.glob("*.pdf"))
        
        if limit:
            pdf_files = pdf_files[:limit]
            
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {papers_dir}")
            
        return pdf_files

    def _initialize_pipeline(
        self, 
        threshold: float, 
        max_iter: int, 
        examples: Optional[str], 
        hybrid_mode: bool
    ) -> HierarchicalExtractionPipeline:
        """Initialize and configure the extraction pipeline."""
        pipeline = HierarchicalExtractionPipeline(
            provider=self.provider,
            model=self.model,
            score_threshold=threshold,
            max_iterations=max_iter,
            verbose=self.verbose,
            examples=examples,
            token_tracker=self.tracker
        )
        
        # COST-001: Enable hybrid mode for local-first extraction
        if hybrid_mode:
            pipeline.set_hybrid_mode(True)
            logger.info("Hybrid mode ENABLED: prioritizing local models (Ollama)")
            
        return pipeline

    def _initialize_vector_store(self, output_path: Path, vectorize: bool) -> Optional[Any]:
        """Initialize vector store if requested."""
        if not vectorize:
            return None
            
        from .vectorizer import ChromaVectorStore
        vector_dir = output_path.parent / "vector_store"
        return ChromaVectorStore(
            collection_name=settings.DEFAULT_COLLECTION_NAME,
            persist_directory=str(vector_dir),
        )

    def _parse_documents(
        self, 
        pdf_files: List[Path], 
        callback: Optional[Callable[[str, Any, str], None]] = None
    ) -> List[ParsedDocument]:
        """Parse PDF documents."""
        parsed_docs = []
        for pdf_path in pdf_files:
            try:
                doc = self.parser.parse_pdf(str(pdf_path))
                parsed_docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to parse {pdf_path.name}: {e}")
                if callback:
                    callback(pdf_path.name, str(e), "failed")
        return parsed_docs

    def _build_summary(
        self, 
        pdf_files: List[Path], 
        parsed_docs: List[ParsedDocument], 
        failed_files: List[Any]
    ) -> Dict[str, Any]:
        """Build extraction summary."""
        summary = self.tracker.get_session_summary()
        return {
            "total_files": len(pdf_files),
            "parsed_files": len(parsed_docs),
            "failed_files": failed_files,
            "cost_usd": summary.get("total_cost_usd", 0.0),
            "tokens": summary.get("total_tokens", 0)
        }

    def _handle_extraction_success(
        self, 
        filename: str, 
        data: Any, 
        writer: csv.DictWriter, 
        file_handle: TextIO,
        vector_store: Optional[Any],
        parsed_docs: List[ParsedDocument],
        fieldnames: List[str],
        callback: Optional[Callable]
    ):
        """Handle successful extraction result (write to CSV and vectorize)."""
        extracted_data = data
        if "final_data" in data:
            extracted_data = data["final_data"]
        
        row = {k: v for k, v in extracted_data.items() if k in fieldnames}
        writer.writerow(row)
        file_handle.flush()
        
        # Handle Vectorization (Non-blocking)
        if vector_store:
            # Find the doc in parsed_docs
            doc = next((d for d in parsed_docs if d.filename == filename), None)
            if doc:
                try:
                    loop = asyncio.get_running_loop()
                    func = functools.partial(vector_store.add_chunks_from_parsed_doc, doc, extracted_data=extracted_data)
                    loop.run_in_executor(None, func)
                except RuntimeError as e:
                    # No event loop - fallback to sync
                    logger.debug(f"No async loop available, using sync vectorization: {e}")
                    vector_store.add_chunks_from_parsed_doc(doc, extracted_data=extracted_data)
                except Exception as e:
                    # Vectorization failed - log but don't fail extraction
                    logger.error(f"Vectorization failed for {filename}: {e}", exc_info=True)
                    
        if callback:
            callback(filename, data, "success")

    def _execute_standard_extraction(
        self,
        batch_executor: BatchExecutor,
        parsed_docs: List[ParsedDocument],
        model: Type[Any],
        theme: str,
        hierarchical: bool,
        workers: int,
        resume: bool,
        result_handler: Callable
    ):
        """Execute standard (non-chunked) extraction."""
        if hierarchical:
            asyncio.run(batch_executor.process_batch_async(
                documents=parsed_docs,
                schema=model,
                theme=theme,
                resume=resume,
                callback=result_handler,
                concurrency_limit=workers
            ))
        else:
            batch_executor.process_batch(
                documents=parsed_docs,
                schema=model,
                theme=theme,
                resume=resume,
                callback=result_handler
            )

    def _execute_chunked_extraction(
        self,
        batch_executor: BatchExecutor,
        parsed_docs: List[ParsedDocument],
        schema_chunks: List[List[FieldDefinition]],
        theme: str,
        hierarchical: bool,
        workers: int,
        writer: csv.DictWriter,
        file_handle: TextIO,
        vector_store: Optional[Any],
        fieldnames: List[str],
        callback: Optional[Callable],
        failed_files: List[Any]
    ):
        """Execute extraction with schema chunking."""
        logger.info(f"Schema chunking enabled: {len(schema_chunks)} chunks")
        
        # Store chunk results per document
        chunk_results_by_doc = {}
        
        for chunk_idx, chunk_fields in enumerate(schema_chunks):
            logger.info(f"Processing chunk {chunk_idx + 1}/{len(schema_chunks)}")
            
            # Build model for this chunk
            ChunkModel = build_extraction_model(chunk_fields, f"ChunkModel_{chunk_idx}")
            
            # Run extraction for this chunk
            def chunk_callback(filename, data, status):
                if status == "success":
                    if filename not in chunk_results_by_doc:
                        chunk_results_by_doc[filename] = []
                    
                    extracted_data = data
                    if "final_data" in data:
                        extracted_data = data["final_data"]
                    
                    chunk_results_by_doc[filename].append(extracted_data)
                else:
                    failed_files.append((filename, f"Chunk {chunk_idx}: {str(data)}"))
            
            if hierarchical:
                asyncio.run(batch_executor.process_batch_async(
                    documents=parsed_docs,
                    schema=ChunkModel,
                    theme=theme,
                    resume=False,  # Don't resume for chunks
                    callback=chunk_callback,
                    concurrency_limit=workers
                ))
            else:
                batch_executor.process_batch(
                    documents=parsed_docs,
                    schema=ChunkModel,
                    theme=theme,
                    resume=False,
                    callback=chunk_callback
                )
        
        # Merge chunk results and write to CSV
        for filename, chunk_results in chunk_results_by_doc.items():
            merged_data = merge_extraction_results(chunk_results)
            self._handle_extraction_success(
                filename, merged_data, writer, file_handle, 
                vector_store, parsed_docs, fieldnames, callback
            )

    def run_extraction(
        self,
        papers_dir: str,
        fields: List[FieldDefinition],
        output_csv: str,
        hierarchical: bool = False,
        theme: str = settings.DEFAULT_THEME,
        threshold: float = settings.SCORE_THRESHOLD,
        max_iter: int = settings.MAX_ITERATIONS,
        workers: int = settings.WORKERS,
        resume: bool = False,
        examples: Optional[str] = None,
        vectorize: bool = True,
        limit: Optional[int] = None,
        hybrid_mode: bool = True,  # COST-001: Enable hybrid local-first extraction
        schema_chunks: Optional[List[List[FieldDefinition]]] = None,  # Schema chunking for cost optimization
        callback: Optional[Callable[[str, Any, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Run the full extraction pipeline on a directory of papers.
        """
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Setup Logging & State
        audit_logger, state_manager = self._setup_extraction_context(output_path)
        
        # 2. Build Model
        ExtractionModel, fieldnames = self._build_extraction_model(fields)
        
        # 3. Load Papers
        pdf_files = self._load_papers(papers_dir, limit)
            
        # 4. Initialize Pipeline & Extractor
        pipeline = self._initialize_pipeline(threshold, max_iter, examples, hybrid_mode)
        
        # 5. Initialize Vector Store
        vector_store = self._initialize_vector_store(output_path, vectorize)
        
        # 6. Initialize Batch Executor
        batch_executor = BatchExecutor(
            pipeline=pipeline,
            state_manager=state_manager,
            max_workers=workers
        )
        
        # 7. Parse PDFs
        parsed_docs = self._parse_documents(pdf_files, callback)

        # 8. Execute Batch
        failed_files = []
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            
            if schema_chunks:
                self._execute_chunked_extraction(
                    batch_executor, parsed_docs, schema_chunks, theme, hierarchical, workers,
                    writer, f, vector_store, fieldnames, callback, failed_files
                )
            else:
                def result_handler(filename, data, status):
                    if status == "success":
                        self._handle_extraction_success(
                            filename, data, writer, f, vector_store, parsed_docs, fieldnames, callback
                        )
                    else:
                        failed_files.append((filename, str(data)))
                        if callback:
                            callback(filename, data, status)
                            
                self._execute_standard_extraction(
                    batch_executor, parsed_docs, ExtractionModel, theme, hierarchical, workers, resume, result_handler
                )
                
        # 9. Return Summary
        return self._build_summary(pdf_files, parsed_docs, failed_files)

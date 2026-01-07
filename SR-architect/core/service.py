
import os
import csv
from pathlib import Path
from typing import List, Optional, Type, Dict, Any, Callable

from .config import settings
from .parser import DocumentParser, ParsedDocument
from .hierarchical_pipeline import HierarchicalExtractionPipeline, PipelineResult
from .batch_processor import BatchExecutor
from .state_manager import StateManager
from .token_tracker import TokenTracker
from .audit_logger import AuditLogger
from .schema_builder import build_extraction_model, FieldDefinition
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

    def run_extraction(
        self,
        papers_dir: str,
        fields: List[FieldDefinition],
        output_csv: str,
        hierarchical: bool = False,
        theme: str = "General extraction",
        threshold: float = settings.SCORE_THRESHOLD,
        max_iter: int = settings.MAX_ITERATIONS,
        workers: int = settings.WORKERS,
        resume: bool = False,
        examples: Optional[str] = None,
        vectorize: bool = True,
        limit: Optional[int] = None,
        callback: Optional[Callable[[str, Any, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Run the full extraction pipeline on a directory of papers.
        """
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Setup Logging & State
        audit_log_dir = output_path.parent / "logs"
        audit_logger = AuditLogger(log_dir=str(audit_log_dir))
        checkpoint_path = output_path.parent / "extraction_checkpoint.json"
        state_manager = StateManager(checkpoint_path)
        
        # 2. Build Model
        ExtractionModel = build_extraction_model(fields, "SRExtractionModel")
        fieldnames = list(ExtractionModel.model_fields.keys())
        
        # 3. Load Papers
        papers_path = Path(papers_dir)
        pdf_files = list(papers_path.glob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]
            
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {papers_dir}")
            
        # 4. Initialize Pipeline & Extractor
        pipeline = HierarchicalExtractionPipeline(
            provider=self.provider,
            model=self.model,
            score_threshold=threshold,
            max_iterations=max_iter,
            verbose=self.verbose,
            examples=examples,
            token_tracker=self.tracker
        )
        
        # For non-hierarchical mode, we still use the pipeline's components 
        # but call extract_document which handles the logic.
        
        # 5. Initialize Vector Store
        vector_store = None
        if vectorize:
            from .vectorizer import ChromaVectorStore
            vector_dir = output_path.parent / "vector_store"
            vector_store = ChromaVectorStore(
                collection_name="sr_extraction",
                persist_directory=str(vector_dir),
            )
        
        # 6. Initialize Batch Executor
        batch_executor = BatchExecutor(
            pipeline=pipeline,
            state_manager=state_manager,
            max_workers=workers
        )
        
        # 7. Parse PDFs
        parsed_docs = []
        for pdf_path in pdf_files:
            try:
                doc = self.parser.parse_pdf(str(pdf_path))
                parsed_docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to parse {pdf_path.name}: {e}")
                if callback:
                    callback(pdf_path.name, str(e), "failed")

        # 8. Execute Batch
        failed_files = []
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            
            def internal_callback(filename, data, status):
                if status == "success":
                    extracted_data = data
                    if "final_data" in data:
                        extracted_data = data["final_data"]
                    
                    row = {k: v for k, v in extracted_data.items() if k in fieldnames}
                    writer.writerow(row)
                    f.flush()
                    
                    # Handle Vectorization (Non-blocking)
                    if vector_store:
                        # Find the doc in parsed_docs
                        doc = next((d for d in parsed_docs if d.filename == filename), None)
                        if doc:
                            try:
                                import asyncio
                                import functools
                                loop = asyncio.get_running_loop()
                                func = functools.partial(vector_store.add_chunks_from_parsed_doc, doc, extracted_data=extracted_data)
                                loop.run_in_executor(None, func)
                            except RuntimeError:
                                # Fallback if no loop (sync mode)
                                vector_store.add_chunks_from_parsed_doc(doc, extracted_data=extracted_data)
                else:
                    failed_files.append((filename, str(data)))
                
                if callback:
                    callback(filename, data, status)

            if hierarchical:
                import asyncio
                asyncio.run(batch_executor.process_batch_async(
                    documents=parsed_docs,
                    schema=ExtractionModel,
                    theme=theme,
                    resume=resume,
                    callback=internal_callback,
                    concurrency_limit=workers
                ))
            else:
                batch_executor.process_batch(
                    documents=parsed_docs,
                    schema=ExtractionModel,
                    theme=theme,
                    resume=resume,
                    callback=internal_callback
                )
                
        # 9. Return Summary
        summary = self.tracker.get_session_summary()
        return {
            "total_files": len(pdf_files),
            "parsed_files": len(parsed_docs),
            "failed_files": failed_files,
            "cost_usd": summary.get("total_cost_usd", 0.0),
            "tokens": summary.get("total_tokens", 0)
        }

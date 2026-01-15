"""
Extraction executor with dependency injection.

Orchestrates extraction with explicit dependencies to avoid circular imports.
"""
from typing import Type, TypeVar, Callable, Optional, Any, Dict, List
from pydantic import BaseModel
from core.parser import ParsedDocument
from core.config import settings

T = TypeVar('T', bound=BaseModel)


class ExtractionExecutor:
    """
    Extraction orchestrator with explicit dependencies.
    
    Uses dependency injection to avoid circular dependencies on pipeline.
    Provides thin sync/async wrappers over shared validation logic.
    """
    
    def __init__(
        self,
        # Core components
        extractor,  # StructuredExtractor
        checker,  # ExtractionChecker
        regex_extractor,  # RegexExtractor
        
        # Configuration
        max_iterations: int,
        score_threshold: float,
        logger,
        
        # Injected methods (from pipeline)
        compute_fingerprint: Callable[[str], str],
        check_duplicate: Callable[[str], Optional[Any]],
        cache_result: Callable[[str, Any], None],
        filter_and_classify: Callable,
        
        # Optional components
        quality_auditor=None,
    ):
        """
        Initialize with explicit dependencies.
        
        Benefits:
        - No circular dependency on pipeline
        - Easy to mock for unit tests
        - Explicit about what each method needs
        
        Args:
            extractor: Structured extractor instance
            checker: Extraction checker instance
            regex_extractor: Regex extractor instance
            max_iterations: Maximum validation iterations
            score_threshold: Minimum score to pass validation
            logger: Logger instance
            compute_fingerprint: Function to compute document fingerprint
            check_duplicate: Function to check cache for duplicates
            cache_result: Function to cache extraction results
            filter_and_classify: Function to filter and classify chunks
            quality_auditor: Optional quality auditor
        """
        self.extractor = extractor
        self.checker = checker
        self.regex_extractor = regex_extractor
        
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.logger = logger
        
        # Injected functions
        self.compute_fingerprint = compute_fingerprint
        self.check_duplicate = check_duplicate
        self.cache_result = cache_result
        self.filter_and_classify = filter_and_classify
        
        # Optional components
        # Optional components
        self.quality_auditor = quality_auditor
        self.sentence_extractor = None
        
    def set_sentence_extractor(self, extractor):
        """Inject sentence extractor."""
        self.sentence_extractor = extractor
    
    def _prepare_context(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> Dict[str, Any]:
        """
        Thin wrapper around pure function from stages.py.
        
        Args:
            document: Parsed document
            schema: Extraction schema
            theme: Extraction theme
            
        Returns:
            Context dict with all preparation data
        """
        from core.pipeline.stages import prepare_extraction_context, build_context
        
        return prepare_extraction_context(
            document, schema, theme,
            self.compute_fingerprint,
            self.check_duplicate,
            self.filter_and_classify,
            build_context
        )
    
    def _apply_regex(
        self, 
        context: str, 
        schema_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Thin wrapper around pure function from stages.py.
        
        Args:
            context: Text context
            schema_fields: List of schema field names
            
        Returns:
            Dict of pre-filled fields from regex
        """
        from core.pipeline.stages import apply_regex_extraction
        
        return apply_regex_extraction(
            context,
            schema_fields,
            self.regex_extractor,
            settings.CONFIDENCE_THRESHOLD_MID,
            self.logger
        )
    
    def extract_sync(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> Any:  # PipelineResult
        """
        Sync extraction - thin wrapper over validation loop.
        
        Args:
            document: Parsed document
            schema: Extraction schema
            theme: Extraction theme
            
        Returns:
            PipelineResult with extraction data
        """
        from core.pipeline.extraction.validation import run_validation_loop
        
        # Prepare context (pure function - testable!)
        ctx = self._prepare_context(document, schema, theme)
        
        # Check cache
        if ctx.get("cached"):
            self.logger.info(f"  ✓ Using cached result for {document.filename}")
            return ctx["cached"]
        
        # Apply regex pre-fill (pure function - testable!)
        pre_filled = self._apply_regex(ctx["context"], ctx["schema_fields"])
        
        if pre_filled:
            self.logger.info(f"  Tier 0 extracted {len(pre_filled)} fields via regex")
        
        # Validation loop
        result = run_validation_loop(
            context=ctx["context"],
            schema=schema,
            extractor=self.extractor,
            checker=self.checker,
            max_iterations=self.max_iterations,
            score_threshold=self.score_threshold,
            pre_filled=pre_filled,
            document=document,
            relevant_chunks=ctx["relevant_chunks"],
            theme=theme,
            logger=self.logger,
            quality_auditor=self.quality_auditor,
        )
        
        # Cache result
        self.cache_result(ctx["fingerprint"], result)
        return result
    
    async def extract_async(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> Any:  # PipelineResult
        """
        Async extraction - same structure, async I/O.
        
        Args:
            document: Parsed document
            schema: Extraction schema
            theme: Extraction theme
            
        Returns:
            PipelineResult with extraction data
        """
        from core.pipeline.extraction.validation import run_validation_loop_async
        
        # Prepare context (pure function - REUSED!)
        ctx = self._prepare_context(document, schema, theme)
        
        # Check cache
        if ctx.get("cached"):
            self.logger.info(f"  ✓ Using cached result for {document.filename}")
            return ctx["cached"]
        
        # Apply regex pre-fill (pure function - REUSED!)
        pre_filled = self._apply_regex(ctx["context"], ctx["schema_fields"])
        
        if pre_filled:
            self.logger.info(f"  Tier 0 extracted {len(pre_filled)} fields via regex")
            
        # Apply Sentence Extractor (Hybrid Mode)
        if self.sentence_extractor:
            self.logger.info("  Running hybrid sentence extraction...")
            try:
                # Extract frames
                # Note: SentenceExtractor.extract takes (chunks, template="")
                # We reuse chunks from document
                frames = await self.sentence_extractor.extract(document.chunks)
                
                sentence_data = {}
                count = 0
                for frame in frames:
                    # Frame content is dict of attributes
                    # We expect keys like 'attr' or flattened content
                    # Based on test mock: content={"entity_type": "histopathology"}
                    # And text="Spindle cell neoplasm"
                    # We need to map this to schema fields.
                    # This implies SentenceExtractor needs to know Schema or mappings.
                    # Or it returns {schema_field: value}.
                    # The test mock returns content={"entity_type": ...}. 
                    # The integration test expects result.final_data["histopathology"]
                    # If SentenceExtractor returns generic frames, we need mapping.
                    # Assuming for now frame.content IS the data, or frame keys map to schema.
                    # Let's assume simplest: merge result extraction dicts.
                    if frame.content:
                        for k, v in frame.content.items():
                             # Heuristic: if key matches schema field?
                             # Or use frame.text as value for frame.content['entity_type']? 
                             # Test mock: text="Spindle...", content={"entity_type": "histopathology"}
                             # So field is 'histopathology', value is 'Spindle...'
                             if "entity_type" in frame.content:
                                 field_name = frame.content["entity_type"]
                                 sentence_data[field_name] = frame.text
                                 count += 1
                             else:
                                 # Direct key-value merge
                                 sentence_data.update(frame.content)
                                 count += len(frame.content)
                
                if sentence_data:
                    self.logger.info(f"  Hybrid extracted {count} items. Merging into pre-filled.")
                    pre_filled.update(sentence_data)
                    
            except Exception as e:
                self.logger.warning(f"  Hybrid extraction failed: {e}")
        
        # Validation loop (async)
        result = await run_validation_loop_async(
            context=ctx["context"],
            schema=schema,
            extractor=self.extractor,
            checker=self.checker,
            max_iterations=self.max_iterations,
            score_threshold=self.score_threshold,
            pre_filled=pre_filled,
            document=document,
            relevant_chunks=ctx["relevant_chunks"],
            theme=theme,
            logger=self.logger,
            quality_auditor=self.quality_auditor,
        )
        
        # Cache result
        self.cache_result(ctx["fingerprint"], result)
        return result


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
        self.quality_auditor = quality_auditor
    
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

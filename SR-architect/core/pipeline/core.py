#!/usr/bin/env python3
"""
Hierarchical Extraction Pipeline - Core Module.

Orchestrates the full extraction workflow:
Filter → Classify → Extract → Check → Iterate

Refactored for clarity with dependency injection and composition patterns.
"""

import hashlib
from datetime import datetime
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel

from core import utils
from core.config import settings
from core.parser import ParsedDocument, DocumentChunk
from core.content_filter import ContentFilter
from core.classification import RelevanceClassifier
from core.data_types import PipelineResult
from core.semantic_chunker import SemanticChunker
from core.extractors import StructuredExtractor
from core.validation import ExtractionChecker
from core.regex_extractor import RegexExtractor
from core.two_pass_extractor import TwoPassExtractor
from core.sentence_extractor import SentenceExtractor

# Agents
from agents.schema_discovery import SchemaDiscoveryAgent
from agents.quality_auditor import QualityAuditorAgent
from agents.meta_analyst import MetaAnalystAgent

# Import extraction executor
from .extraction import ExtractionExecutor

T = TypeVar('T', bound=BaseModel)


class HierarchicalExtractionPipeline:
    """
    Full pipeline: Filter → Classify → Extract → Check → Iterate.
    
    Uses composition pattern with ExtractionExecutor for extraction logic.
    Maintains backward compatibility with original interface.
    """
    
    def __init__(
        self,
        provider: str = settings.LLM_PROVIDER,
        model: Optional[str] = None,
        score_threshold: float = settings.SCORE_THRESHOLD,
        max_iterations: int = settings.MAX_ITERATIONS,
        verbose: bool = False,
        examples: Optional[str] = None,
        quality_auditor: Optional[QualityAuditorAgent] = None,
        schema_discoverer: Optional[SchemaDiscoveryAgent] = None,
        meta_analyst: Optional[MetaAnalystAgent] = None,
        token_tracker: Optional["TokenTracker"] = None,
    ):
        """
        Initialize the hierarchical pipeline.
        
        Args:
            provider: LLM provider (e.g., 'openai', 'anthropic')
            model: Model name (if None, uses provider-specific default)
            score_threshold: Minimum confidence score to accept extraction
            max_iterations: Maximum feedback loops for validation
            verbose: Enable debug logging
            examples: Few-shot examples string
            quality_auditor: Optional injected QualityAuditorAgent
            schema_discoverer: Optional injected SchemaDiscoveryAgent
            meta_analyst: Optional injected MetaAnalystAgent
            token_tracker: Optional token usage tracker
        """
        # Resolve model name if not provided
        if model is None:
            model = settings.get_model_for_provider(provider)
        
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize TokenTracker if not provided
        if token_tracker is None:
            from core.token_tracker import TokenTracker
            self.token_tracker = TokenTracker()
        else:
            self.token_tracker = token_tracker
            
        # Initialize components
        self.content_filter = ContentFilter()
        self.relevance_classifier = RelevanceClassifier(
            provider=provider,
            model=model,
            token_tracker=self.token_tracker,
        )
        self.extractor = StructuredExtractor(
            provider=provider,
            model=model,
            examples=examples,
            token_tracker=self.token_tracker,
        )
        self.checker = ExtractionChecker(
            provider=provider,
            model=model,
            token_tracker=self.token_tracker,
        )
        
        # Use injected agents or create defaults
        self.quality_auditor = quality_auditor or QualityAuditorAgent(
            provider=provider, 
            model=model if model != "anthropic/claude-3-haiku" else "anthropic/claude-3.5-sonnet",
            token_tracker=self.token_tracker
        )
        self.schema_discoverer = schema_discoverer or SchemaDiscoveryAgent(
            provider=provider, 
            model=model,
            token_tracker=self.token_tracker
        )
        self.meta_analyst = meta_analyst or MetaAnalystAgent(
            provider=provider, 
            model=model,
            token_tracker=self.token_tracker
        )
        
        # Initialize two-pass extractor for hybrid mode
        self.two_pass_extractor = TwoPassExtractor(
            local_model="qwen3:14b",
            cloud_model="gpt-4o-mini",
        )
        self.hybrid_mode = False
        
        # Initialize Tier 0 regex extractor
        self.regex_extractor = RegexExtractor()
        
        # Initialize sentence extractor
        self.sentence_extractor = SentenceExtractor(
            provider=provider,
            model=model,
            token_tracker=self.token_tracker
        )
        
        # Initialize semantic chunker
        self.semantic_chunker = SemanticChunker(
            client=utils.get_async_llm_client(provider=provider)
        )
        
        # Document fingerprint cache for duplicate detection
        self._fingerprint_cache: Dict[str, PipelineResult] = {}
        
        self.logger = utils.get_logger("HierarchicalPipeline")
        
        # Initialize extraction executor with dependency injection
        self._extraction_executor = ExtractionExecutor(
            extractor=self.extractor,
            checker=self.checker,
            regex_extractor=self.regex_extractor,
            max_iterations=self.max_iterations,
            score_threshold=self.score_threshold,
            logger=self.logger,
            compute_fingerprint=self._compute_fingerprint,
            check_duplicate=self._check_duplicate,
            cache_result=self._cache_result,
            filter_and_classify=self._filter_and_classify,
            quality_auditor=self.quality_auditor,
        )
    
    def set_hybrid_mode(self, enabled: bool = True):
        """
        Enable or disable hybrid extraction mode.
        
        When enabled, uses TwoPassExtractor for local-first extraction.
        
        Args:
            enabled: Whether to enable hybrid mode
        """
        self.hybrid_mode = enabled
        
        # Inject sentence extractor into executor if hybrid mode is enabled
        if enabled:
            self._extraction_executor.set_sentence_extractor(self.sentence_extractor)
        else:
            self._extraction_executor.set_sentence_extractor(None)
    
    def segment_document(self, text: str, doc_id: Optional[str] = None):
        """
        Segment the document into logical sections using LLM-based semantic chunking.
        
        Args:
            text: Document text to segment
            doc_id: Optional document ID for tracking
            
        Returns:
            Segmented document chunks
        """
        return self.semantic_chunker.chunk(text, doc_id=doc_id)
    
    def _compute_fingerprint(self, text: str, max_chars: int = None) -> str:
        """
        Compute document fingerprint for duplicate detection.
        
        Uses SHA256 hash of first N characters to identify duplicates.
        
        Args:
            text: Document text
            max_chars: Maximum characters to use for fingerprint
            
        Returns:
            SHA256 hash string
        """
        if max_chars is None:
            max_chars = settings.CACHE_HASH_CHARS
        
        sample = text[:max_chars]
        return hashlib.sha256(sample.encode()).hexdigest()
    
    def _check_duplicate(self, fingerprint: str) -> Optional[PipelineResult]:
        """
        Check if document has already been processed.
        
        Args:
            fingerprint: Document fingerprint
            
        Returns:
            Cached PipelineResult if duplicate, None otherwise
        """
        return self._fingerprint_cache.get(fingerprint)
    
    def _cache_result(self, fingerprint: str, result: PipelineResult):
        """
        Cache extraction result by fingerprint.
        
        Args:
            fingerprint: Document fingerprint
            result: Pipeline result to cache
        """
        self._fingerprint_cache[fingerprint] = result
    
    def _filter_and_classify(
        self, 
        document: ParsedDocument, 
        theme: str, 
        schema_fields: List[str]
    ) -> tuple:
        """
        Stage 1 & 2: Filter content and classify relevance.
        
        Args:
            document: Parsed document to process
            theme: Extraction theme
            schema_fields: List of schema field names
            
        Returns:
            Tuple of (relevant_chunks, filter_stats, relevance_stats, warnings)
        """
        warnings = []
        
        # Stage 1: Filter
        filter_result = self.content_filter.filter_chunks(document.chunks)
        filtered_chunks = filter_result.filtered_chunks
        
        if not filtered_chunks:
            warnings.append("All chunks were filtered out - using original chunks")
            filtered_chunks = document.chunks
        
        # Stage 2: Classify relevance
        relevant_chunks, relevance_results = self.relevance_classifier.get_relevant_chunks(
            filtered_chunks, theme, schema_fields
        )
        relevance_stats = self.relevance_classifier.get_classification_summary(relevance_results)
        
        if not relevant_chunks:
            warnings.append("No chunks classified as relevant - using all filtered chunks")
            relevant_chunks = filtered_chunks
            
        return relevant_chunks, filter_result.token_stats, relevance_stats, warnings
    
    def extract_document(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str,
    ) -> PipelineResult:
        """
        Full extraction with validation loop (sync version).
        
        Delegates to ExtractionExecutor for extraction logic.
        
        Args:
            document: Parsed document to extract from
            schema: Pydantic schema defining extraction fields
            theme: Meta-analysis theme (e.g., "medical case report")
            
        Returns:
            PipelineResult with extracted data and validation metrics
        """
        self.logger.info(f"Starting extraction for: {document.filename}")
        return self._extraction_executor.extract_sync(document, schema, theme)
    
    async def extract_document_async(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str,
    ) -> PipelineResult:
        """
        Full extraction with validation loop (async version).
        
        Delegates to ExtractionExecutor for extraction logic.
        
        Args:
            document: Parsed document to extract from
            schema: Pydantic schema defining extraction fields
            theme: Meta-analysis theme (e.g., "medical case report")
            
        Returns:
            PipelineResult with extracted data and validation metrics
        """
        self.logger.info(f"Starting async extraction for: {document.filename}")
        return await self._extraction_executor.extract_async(document, schema, theme)
    
    def extract_from_text(
        self,
        text: str,
        schema: Type[T],
        theme: str,
        filename: str = "document",
    ) -> PipelineResult:
        """
        Extract from raw text (simplified interface).
        
        Convenience method that creates a ParsedDocument from text.
        
        Args:
            text: Raw document text
            schema: Extraction schema
            theme: Meta-analysis theme
            filename: Source filename for tracking
            
        Returns:
            PipelineResult
        """
        from core.parser import DocumentChunk
        
        # Create simple parsed document
        chunks = [DocumentChunk(
            text=text,
            page=1,
            section="full_text",
            chunk_index=0
        )]
        
        document = ParsedDocument(
            filename=filename,
            full_text=text,
            chunks=chunks,
            metadata={}
        )
        
        return self.extract_document(document, schema, theme)
    
    async def extract_from_text_async(
        self,
        text: str,
        schema: Type[T],
        theme: str,
        filename: str = "document",
    ) -> PipelineResult:
        """
        Async version of extract_from_text.
        
        Args:
            text: Raw document text
            schema: Extraction schema
            theme: Meta-analysis theme
            filename: Source filename for tracking
            
        Returns:
            PipelineResult
        """
        from core.parser import DocumentChunk
        
        # Create simple parsed document
        chunks = [DocumentChunk(
            text=text,
            page=1,
            section="full_text",
            chunk_index=0
        )]
        
        document = ParsedDocument(
            filename=filename,
            full_text=text,
            chunks=chunks,
            metadata={}
        )
        
        return await self.extract_document_async(document, schema, theme)
    
    def discover_schema(self, papers_dir: str, sample_size: int = 3):
        """
        Run adaptive schema discovery.
        
        Args:
            papers_dir: Directory containing sample papers
            sample_size: Number of papers to sample
            
        Returns:
            Discovered schema definition
        """
        return self.schema_discoverer.discover_schema(papers_dir, sample_size)

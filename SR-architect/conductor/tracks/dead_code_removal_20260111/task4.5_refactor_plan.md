# Task 4.5: Split hierarchical_pipeline.py - Detailed Refactoring Plan

**Date**: 2026-01-12  
**File**: hierarchical_pipeline.py (860 lines)  
**Strategy**: Composition pattern for sync/async code reuse

---

## Phase 1: Critique (Code Smell Analysis)

### Current Issues

1. **File Size**: 860 lines (CRITICAL - exceeds 400-line threshold by 115%)
2. **Large Functions**: 
   - `extract_document` (200 lines) - Lines 298-497
   - `extract_document_async` (258 lines) - Lines 499-756
3. **Code Duplication**: 90% overlap between sync/async extraction methods
4. **Multiple Responsibilities**:
   - Pipeline orchestration
   - Context building
   - Filtering and classification
   - Extraction execution
   - Caching and duplicate detection
   - Agent integration

---

## Phase 2: Proposed Refactoring Plan

### New Structure (UPDATED)

```
core/pipeline/
  __init__.py           # Export HierarchicalExtractionPipeline (10 lines)
  core.py              # Class init, caching, context building (200 lines)
  stages.py            # Pure functions for stage logic (150 lines)
  extraction/
    __init__.py        # Export ExtractionExecutor (5 lines)
    executor.py        # Main orchestration with DI (150 lines)
    validation.py      # Validation loop logic (100 lines)
    helpers.py         # Pure helper functions (50 lines)
```

**Rationale for extraction/ subdirectory**:
- Keeps extraction.py components under 200 lines each
- Better separation of concerns
- Easier to navigate and test

### File Split Mapping (UPDATED)

#### 1. pipeline/__init__.py (10 lines)
```python
"""
Hierarchical extraction pipeline module.
"""
from .core import HierarchicalExtractionPipeline

__all__ = ['HierarchicalExtractionPipeline']
```

#### 2. pipeline/core.py (200 lines)
**Contents**:
- Lines 1-47: Imports and type definitions
- Lines 48-155: `HierarchicalExtractionPipeline.__init__`
- Lines 157-164: `set_hybrid_mode`
- Lines 166-170: `segment_document`
- Lines 172-186: `_compute_fingerprint`
- Lines 188-201: `_check_duplicate`
- Lines 203-205: `_cache_result`
- Lines 821-828: `discover_schema` (agent integration)

**Responsibilities**:
- Pipeline initialization
- Component wiring (extractor, checker, filter, classifier)
- Caching and duplicate detection
- Agent integration (schema discovery)

#### 3. pipeline/stages.py (150 lines) - PURE FUNCTIONS
**Contents**:
- Lines 207-227: `build_context` (extracted as pure function)
- Lines 229-266: `filter_and_classify` (extracted as pure function)
- Lines 268-295: `apply_audit_penalty` (extracted as pure function)
- NEW: `prepare_extraction_context` (pure function)

**Responsibilities**:
- Pure functions with no side effects
- Context building from chunks
- Stage 1: Content filtering
- Stage 2: Relevance classification
- Quality audit integration

#### 4. pipeline/extraction/executor.py (150 lines) - DEPENDENCY INJECTION
**Contents**:
- `ExtractionExecutor` class with explicit dependencies
- Thin sync/async wrappers

**Responsibilities**:
- Extraction orchestration
- Dependency injection (no pipeline reference)

#### 5. pipeline/extraction/validation.py (100 lines)
**Contents**:
- Validation loop logic
- Iteration management
- Result building

#### 6. pipeline/extraction/helpers.py (50 lines)
**Contents**:
- Pure helper functions
- Regex extraction logic
- Revision prompt building

---

## Phase 3: Composition Pattern Implementation

### Problem: 90% Code Duplication

**Current**:
- `extract_document` (sync): 200 lines
- `extract_document_async` (async): 258 lines
- Overlap: ~180 lines of identical logic

### Solution: Extract Shared Logic

```python
# pipeline/extraction.py
class ExtractionExecutor:
    """Shared extraction logic - composition over inheritance."""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.extractor = pipeline.extractor
        self.checker = pipeline.checker
        self.regex_extractor = pipeline.regex_extractor
        self.logger = pipeline.logger
    
    def _prepare_extraction_context(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> Dict[str, Any]:
        """
        Pure function: Build extraction context (no I/O).
        Reusable in both sync and async paths.
        
        Returns:
            Dict with keys: relevant_chunks, context, schema_fields, 
                           filter_stats, relevance_stats, warnings
        """
        # Check for duplicates
        fingerprint = self.pipeline._compute_fingerprint(document.full_text)
        cached = self.pipeline._check_duplicate(fingerprint)
        if cached:
            return {"cached": cached, "fingerprint": fingerprint}
        
        # Extract schema fields
        schema_fields = list(schema.model_fields.keys())
        
        # Stage 1 & 2: Filter and classify
        relevant_chunks, filter_stats, relevance_stats, warnings = \
            self.pipeline._filter_and_classify(document, theme, schema_fields)
        
        # Build context
        context = self.pipeline._build_context(relevant_chunks)
        
        return {
            "relevant_chunks": relevant_chunks,
            "context": context,
            "schema_fields": schema_fields,
            "filter_stats": filter_stats,
            "relevance_stats": relevance_stats,
            "warnings": warnings,
            "fingerprint": fingerprint,
            "cached": None
        }
    
    def _build_revision_prompts(
        self, 
        checker_result: CheckerResult, 
        iteration: int
    ) -> List[str]:
        """Build revision prompts from checker feedback."""
        if not checker_result.suggestions:
            return []
        
        revision_prompt = self.checker.format_revision_prompt(checker_result)
        return [revision_prompt]
    
    def _apply_regex_extraction(
        self, 
        context: str, 
        schema_fields: List[str]
    ) -> Dict[str, Any]:
        """Extract fields using regex patterns (pre-fill)."""
        regex_results = self.regex_extractor.extract_all(context)
        pre_filled = {}
        
        for field_name, result in regex_results.items():
            if result.confidence >= settings.CONFIDENCE_THRESHOLD_MID:
                pre_filled[field_name] = result.value
                self.logger.info(
                    f"  Regex extracted {field_name}: {result.value} "
                    f"(conf={result.confidence:.2f})"
                )
        
        return pre_filled
    
    # Sync wrapper
    def extract_sync(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> PipelineResult:
        """Sync extraction - thin wrapper over shared logic."""
        # Prepare context (pure function)
        ctx = self._prepare_extraction_context(document, schema, theme)
        
        # Check cache
        if ctx.get("cached"):
            return ctx["cached"]
        
        # Apply regex pre-fill
        pre_filled = self._apply_regex_extraction(
            ctx["context"], 
            ctx["schema_fields"]
        )
        
        # Validation loop
        iteration = 0
        revision_prompts = []
        
        while iteration < self.pipeline.max_iterations:
            # LLM extraction (sync I/O)
            extraction = self.extractor.extract_with_evidence(
                text=ctx["context"],
                schema=schema,
                filename=document.filename,
                revision_prompts=revision_prompts,
                pre_filled_fields=pre_filled
            )
            
            # Validation (sync I/O)
            check_result = self.checker.check(
                source_chunks=ctx["relevant_chunks"],
                extracted_data=extraction.extracted_data,
                evidence=extraction.evidence_dicts,
                theme=theme,
                threshold=self.pipeline.score_threshold
            )
            
            # Check if passed
            if check_result.passed:
                result = self._build_pipeline_result(
                    document, extraction, check_result, ctx, iteration
                )
                self.pipeline._cache_result(ctx["fingerprint"], result)
                return result
            
            # Build revision prompts
            revision_prompts = self._build_revision_prompts(
                check_result, iteration
            )
            iteration += 1
        
        # Max iterations reached
        return self._build_failed_result(document, ctx, iteration)
    
    # Async wrapper
    async def extract_async(
        self, 
        document: ParsedDocument, 
        schema: Type[T], 
        theme: str
    ) -> PipelineResult:
        """Async extraction - same structure, async I/O."""
        # Prepare context (pure function - reused!)
        ctx = self._prepare_extraction_context(document, schema, theme)
        
        # Check cache
        if ctx.get("cached"):
            return ctx["cached"]
        
        # Apply regex pre-fill (pure function - reused!)
        pre_filled = self._apply_regex_extraction(
            ctx["context"], 
            ctx["schema_fields"]
        )
        
        # Validation loop
        iteration = 0
        revision_prompts = []
        
        while iteration < self.pipeline.max_iterations:
            # LLM extraction (async I/O)
            extraction = await self.extractor.extract_with_evidence_async(
                text=ctx["context"],
                schema=schema,
                filename=document.filename,
                revision_prompts=revision_prompts,
                pre_filled_fields=pre_filled
            )
            
            # Validation (async I/O)
            check_result = await self.checker.check_async(
                source_chunks=ctx["relevant_chunks"],
                extracted_data=extraction.extracted_data,
                evidence=extraction.evidence_dicts,
                theme=theme,
                threshold=self.pipeline.score_threshold
            )
            
            # Check if passed
            if check_result.passed:
                result = self._build_pipeline_result(
                    document, extraction, check_result, ctx, iteration
                )
                self.pipeline._cache_result(ctx["fingerprint"], result)
                return result
            
            # Build revision prompts (pure function - reused!)
            revision_prompts = self._build_revision_prompts(
                check_result, iteration
            )
            iteration += 1
        
        # Max iterations reached
        return self._build_failed_result(document, ctx, iteration)
```

### Benefits of Composition Pattern

1. **Code Reuse**: 180 lines of shared logic extracted
2. **Maintainability**: Fix bugs in one place
3. **Testability**: Can unit test `_prepare_extraction_context` independently
4. **Readability**: Sync/async wrappers are ~50 lines each (down from 200+)
5. **Consistency**: Identical behavior guaranteed between sync/async

---

## Phase 4: Execution Steps (UPDATED)

### Step 1: Create Directory Structure
```bash
mkdir -p core/pipeline/extraction
touch core/pipeline/__init__.py
touch core/pipeline/core.py
touch core/pipeline/stages.py
touch core/pipeline/extraction/__init__.py
touch core/pipeline/extraction/executor.py
touch core/pipeline/extraction/validation.py
touch core/pipeline/extraction/helpers.py
```

### Step 2: Use Git MV to Preserve History
```bash
# Preserve git history by using git mv
git mv core/hierarchical_pipeline.py core/pipeline/core.py

# Commit the move first
git commit -m "refactor: Move hierarchical_pipeline.py to pipeline/core.py"

# Now split the file in-place
# This preserves git blame history for each split
```

### Step 3: Extract Pure Functions to stages.py
- Extract `_build_context` as pure function
- Extract `_filter_and_classify` wrapper
- Create `prepare_extraction_context` pure function
- Create `apply_regex_extraction` pure function
- Update imports to use relative imports

### Step 4: Create Extraction Module
- Create `extraction/executor.py` with dependency injection
- Create `extraction/validation.py` with loop logic
- Create `extraction/helpers.py` with pure helpers
- Update `extraction/__init__.py` to export `ExtractionExecutor`

### Step 5: Update Core Pipeline
- Update `core.py` to use `ExtractionExecutor`
- Wire dependencies via dependency injection
- Remove old `extract_document` methods
- Delegate to `ExtractionExecutor.extract_sync/async`

### Step 6: Update Imports Across Codebase
```bash
# Find all imports
grep -r "from core.hierarchical_pipeline import" .
grep -r "from core import hierarchical_pipeline" .

# Update to:
# from core.pipeline import HierarchicalExtractionPipeline
```

### Step 7: Run Tests and Commit
```bash
# Run full test suite
pytest tests/ -v --cov=core.pipeline

# If all pass, commit
git add -A
git commit -m "refactor: Split hierarchical_pipeline into pipeline module with DI"
```

---

## Phase 5: Testing Strategy (UPDATED)

### Baseline Tests (Before Split)
```bash
# Run existing tests to establish baseline
pytest tests/ -v -k "pipeline or extraction" --cov=core.hierarchical_pipeline

# Expected: All tests pass
```

### Post-Split Tests
```bash
# Run same tests with new module path
pytest tests/ -v -k "pipeline or extraction" --cov=core.pipeline

# Expected: Same coverage, all tests pass
```

### New Unit Tests for Pure Functions
```python
# tests/unit/pipeline/test_stages.py
from core.pipeline.stages import prepare_extraction_context, build_context

def test_build_context_pure():
    """Test pure function - no I/O, fully deterministic."""
    chunks = [MockChunk("text1"), MockChunk("text2")]
    result = build_context(chunks, max_chars=1000)
    
    assert "text1" in result
    assert "text2" in result

def test_prepare_extraction_context_pure():
    """Test pure function with mocked dependencies."""
    mock_compute = lambda text: "fingerprint123"
    mock_check = lambda fp: None
    mock_filter = lambda doc, theme, fields: ([], {}, {}, [])
    mock_build = lambda chunks: "context"
    
    ctx = prepare_extraction_context(
        mock_doc, mock_schema, "theme",
        mock_compute, mock_check, mock_filter, mock_build
    )
    
    assert ctx["fingerprint"] == "fingerprint123"
    assert ctx["context"] == "context"
```

### Sync/Async Parity Test (NEW)
```python
# tests/integration/test_sync_async_parity.py
import pytest
import asyncio
from core.pipeline import HierarchicalExtractionPipeline

def test_extraction_parity(sample_document, sample_schema):
    """
    Ensure sync and async produce identical results.
    Critical for verifying composition pattern correctness.
    """
    pipeline = HierarchicalExtractionPipeline()
    theme = "medical case report"
    
    # Run sync
    sync_result = pipeline.extract_document(
        sample_document, sample_schema, theme
    )
    
    # Run async
    async_result = asyncio.run(
        pipeline.extract_document_async(
            sample_document, sample_schema, theme
        )
    )
    
    # Compare (excluding timing metadata)
    assert sync_result.extracted_data == async_result.extracted_data
    assert sync_result.passed == async_result.passed
    assert sync_result.quality_score == async_result.quality_score
    assert sync_result.iteration_count == async_result.iteration_count
    
    # Verify evidence is identical
    assert len(sync_result.evidence) == len(async_result.evidence)
```

---

## Success Criteria

1. ✅ All existing tests pass
2. ✅ No files >400 lines
3. ✅ Sync/async duplication eliminated
4. ✅ Imports updated across codebase
5. ✅ Git history preserved (use `git mv` where possible)

---

## Risk Mitigation

1. **Circular Imports**: Use relative imports within pipeline/
2. **Import Breakage**: Search codebase for all imports before changing
3. **Test Failures**: Run tests after each step, rollback if needed
4. **Git History**: Commit after each successful step

---

## Estimated Time

- Step 1-2: 1 hour (directory setup, move core.py)
- Step 3-4: 2 hours (stages.py, extraction.py with composition)
- Step 5-6: 1 hour (init, update imports)
- Step 7: 30 minutes (cleanup, final tests)

**Total**: ~4.5 hours

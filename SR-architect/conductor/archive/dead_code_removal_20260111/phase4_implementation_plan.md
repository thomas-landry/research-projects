# Phase 4 Implementation Plan: Code Smell Remediation

**Date**: 2026-01-11  
**Status**: Ready for Implementation  
**Strategy**: 80/20 Rule - Focus on critical path first

---

## Implementation Priority (User-Approved)

### Phase 4A: Extract Magic Numbers (DO FIRST) 🔴
- **Time**: 2 hours
- **Risk**: Minimal - pure substitution
- **Why First**: Makes all subsequent changes easier; no behavioral changes

### Phase 4B: Split Critical Path Files 🔴
- **Time**: 15 hours (updated)
- **Risk**: Medium - but critical path bottleneck
- **Files**: hierarchical_pipeline.py, extractor.py, extraction_checker.py, batch_processor.py

### Phase 4C: Split Remaining Large Files 🟡
- **Time**: 8 hours
- **Risk**: Low
- **Files**: parser.py, binary_deriver.py, relevance_classifier.py

### Phase 4D: Extract Large Functions 🟡
- **Time**: 6 hours
- **Risk**: Low
- **Functions**: service.py::run_extraction, extractor.py::extract_with_evidence

### Phase 4E: Fix Deep Nesting 🟢
- **Time**: 4 hours
- **Risk**: Low
- **Files**: vectorizer.py, extraction_checker.py, study_classifier.py

---

## Phase 4A: Extract Magic Numbers (TASK 4.0 - NEW)

### Step 1: Create constants.py

```python
# core/constants.py
"""
Algorithm constants for SR-Architect.
These are domain-specific values that rarely change.
"""

# === LLM Retry Logic ===
MAX_LLM_RETRIES = 3
MAX_LLM_RETRIES_ASYNC = 2

# === Validation Weights ===
VALIDATION_WEIGHT_COMPLETENESS = 0.6
VALIDATION_WEIGHT_ACCURACY = 0.4

# === Token Estimation ===
# Already in config.py - keep there

# === Batch Processing ===
DEFAULT_BATCH_SIZE = 10
DEFAULT_PREVIEW_CHARS = 500

# === Sentence Extraction ===
SENTENCE_CONTEXT_WINDOW = 2
SENTENCE_CONCURRENCY_LIMIT = 10
```

### Step 2: Update config.py

```python
# Add to core/config.py

# ========== Extraction Thresholds ==========
CONFIDENCE_THRESHOLD_HIGH: float = Field(
    default=0.95,
    description="High confidence threshold for extraction acceptance"
)
CONFIDENCE_THRESHOLD_MID: float = Field(
    default=0.90,
    description="Medium confidence threshold for regex extraction"
)
EXTRACTION_MIN_CONFIDENCE: float = Field(
    default=0.9,
    description="Minimum confidence for validation"
)

# ========== Context and Chunk Limits ==========
MAX_CONTEXT_CHARS: int = Field(
    default=15000,
    description="Maximum characters for extraction context"
)
MAX_CHUNK_CHARS: int = Field(
    default=8000,
    description="Maximum characters per chunk for validation"
)
MAX_VALIDATION_CHARS: int = Field(
    default=10000,
    description="Maximum characters for validation context"
)

# ========== Parser Settings ==========
DOCLING_CHUNK_SIZE: int = Field(
    default=1000,
    description="Chunk size for Docling parser"
)
DOCLING_MAX_CHARS: int = Field(
    default=15000,
    description="Maximum characters for Docling parsing"
)

# ========== Cache Settings ==========
CACHE_HASH_CHARS: int = Field(
    default=10000,
    description="Characters to use for document hash computation"
)
```

### Step 3: Replace Magic Numbers (File by File)

**Order** (15+ files):
1. hierarchical_pipeline.py (0.90, 0.95, 15000, 8000, 10000)
2. extraction_checker.py (0.6, 0.4, 0.9, 8000, 2)
3. parser.py (1000, 15000, 100)
4. extractor.py (2, 3)
5. cache_manager.py (10000)
6. content_filter.py (4.0)
7. relevance_classifier.py (10, 500)
8. sentence_extractor.py (2, 10)
9. (Continue with remaining files)

**Test Checkpoint After Each File**:
```bash
pytest tests/integration/ -v
```

---

## Phase 4B: Split Critical Path Files

### Task 4.5: Split hierarchical_pipeline.py (858 lines)

**New Structure**:
```
core/pipeline/
  __init__.py           # Export HierarchicalExtractionPipeline
  core.py              # Class init, _build_context, _filter_and_classify
  extraction.py        # Extraction executor with composition pattern
  stages.py            # Stage helper methods
```

**Composition Pattern for Sync/Async**:

```python
# pipeline/extraction.py
class ExtractionExecutor:
    """Shared extraction logic - composition over inheritance."""
    
    def _prepare_extraction(self, doc, context):
        """Pure function: no I/O, reusable in sync/async."""
        filtered = self._filter_and_classify(context)
        return self._build_prompt(filtered)
    
    def extract_sync(self, doc):
        """Sync wrapper - thin layer over shared logic."""
        prompt = self._prepare_extraction(doc, self.context)
        return self.llm.extract(prompt)  # requests
    
    async def extract_async(self, doc):
        """Async wrapper - thin layer over shared logic."""
        prompt = self._prepare_extraction(doc, self.context)
        return await self.async_llm.extract(prompt)  # httpx
```

**Test Checkpoint**:
```bash
# Before splitting
pytest tests/integration/test_extraction_pipeline.py --cov=core.hierarchical_pipeline -v

# After splitting - should have identical coverage
pytest tests/integration/test_extraction_pipeline.py --cov=core.pipeline -v
```

---

### Task 4.6: Split extractor.py (696 lines)

**New Structure**:
```
core/extractors/
  __init__.py
  base.py              # SimpleExtractor, shared methods
  evidence.py          # EvidenceExtractor (sync/async with composition)
  retry.py             # RetryMixin for exponential backoff
```

**Sync/Async Pattern**: Same as pipeline - shared `_build_evidence_prompt`, thin sync/async wrappers

**Test Checkpoint**:
```bash
pytest tests/integration/test_extractor.py --cov=core.extractors -v
```

---

### Task 4.7: Split extraction_checker.py (509 lines)

**New Structure**:
```
core/validation/
  __init__.py
  checker.py           # Core ExtractionChecker class
  validators.py        # _validate_completeness, _validate_accuracy
  formatters.py        # _format_validation_result
```

**Ambiguous Variable Renames**:
- `v` → `validation_score`
- `item` → `field_result`

**De-nesting**: Use early returns in validation loops

**Test Checkpoint**:
```bash
pytest tests/integration/test_extraction_checker.py --cov=core.validation -v
```

---

### Task 4.9: Refactor batch_processor.py (280 lines) - ADDED TO CRITICAL PATH

**Rationale**: 5-level deep nesting blocks debugging; sync/async duplication contradicts composition pattern being applied pipeline-wide.

**Issues**:
1. Deep nesting (5 levels) in `_execute_single_async` (lines 224-272)
2. Large function (54 lines)
3. 90% code duplication between sync and async methods

**Refactoring Strategy**:

```python
# batch_processor.py - Extract ExecutionHandler
class ExecutionHandler:
    """Shared execution logic - composition over duplication."""
    
    def serialize_result(self, result) -> dict:
        """Pure function - reusable sync/async."""
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        elif hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, dict):
            return result
        return result.__dict__
    
    def handle_success(self, doc, serialized):
        """State updates - works sync/async."""
        self.state_manager.update_result(doc.filename, serialized, status="success")
        logger.info(f"✓ Completed {doc.filename}")
    
    def handle_error(self, doc, error, error_type: str):
        """Unified error handling."""
        error_payload = {"error": str(error), "error_type": error_type}
        self.state_manager.update_result(doc.filename, error_payload, status="failed")
        logger.error(f"✗ Failed {doc.filename}: {error}")
        return (doc.filename, error_payload, "failed")

class BatchExecutor:
    def __init__(self, ...):
        self.handler = ExecutionHandler(state_manager)
    
    def _execute_single(self, doc):
        """Sync wrapper - thin, delegates to handler."""
        try:
            result = self.pipeline.extract_document(doc)
            serialized = self.handler.serialize_result(result)
            self.handler.handle_success(doc, serialized)
            return (doc.filename, serialized, "success")
        except MemoryError as e:
            return self.handler.handle_error(doc, e, "memory_error")
        except Exception as e:
            return self.handler.handle_error(doc, e, "error")
    
    async def _execute_single_async(self, doc, semaphore):
        """Async wrapper - same structure, different I/O."""
        async with semaphore:
            try:
                result = await self.pipeline.extract_document_async(doc)
                serialized = self.handler.serialize_result(result)
                self.handler.handle_success(doc, serialized)
                return (doc.filename, serialized, "success")
            except MemoryError as e:
                return self.handler.handle_error(doc, e, "memory_error")
            except Exception as e:
                return self.handler.handle_error(doc, e, "error")
```

**Benefits**:
- Reduces nesting from 5 → 3 levels
- Eliminates 80+ lines of duplication
- Centralizes error handling logic
- Matches composition pattern from hierarchical_pipeline.py
- Easy to unit test `ExecutionHandler` independently

**Test Checkpoint**:
```bash
pytest tests/ -v -k "batch" --cov=core.batch_processor
```

---

## Phase 4C: Split Remaining Large Files

### Task 4.8: Split parser.py (500 lines)

**New Structure**:
```
core/parsers/
  __init__.py
  base.py              # BasePDFParser ABC
  docling.py           # DoclingParser (primary)
  fallbacks.py         # PyMuPDFParser, PDFPlumberParser
```

**Strategy Pattern**: Iterate through parsers in order; first success wins

---

### Task 4.12: Split binary_deriver.py (603 lines)

**New Structure**:
```
core/binary/
  __init__.py
  core.py              # BinaryDeriver class
  rules.py             # Rule definitions and patterns
```

---

### Task 4.13: Split relevance_classifier.py (470 lines)

**New Structure**:
```
core/classification/
  __init__.py
  classifier.py        # RelevanceClassifier class
  helpers.py           # Helper methods, formatting
```

---

## Phase 4D: Extract Large Functions

### Task 4.3: Extract service.py::run_extraction (226 lines)

```python
def run_extraction(self, ...):
    """Main extraction orchestrator - now readable!"""
    setup = self._setup_extraction_context(db, path, config)
    docs = self._parse_documents(setup)
    results = self._execute_extractions(docs, setup)
    self._handle_callbacks(results, setup)
    if vectorize:
        self._vectorize_results(results, setup)
    return results

# Each helper ~40-50 lines, much easier to test
```

**Test**: Existing `test_service.py` integration tests unchanged

---

### Task 4.14: Extract extractor.py::extract_with_evidence (128 lines)

Extract into:
- `_build_evidence_prompt()` - Prompt construction
- `_parse_evidence_response()` - Response parsing
- `_validate_evidence()` - Evidence validation

---

## Phase 4E: Fix Deep Nesting

### Task 4.15: Fix vectorizer.py deep nesting

**Approach**: Extract nested loops into `_process_batch()`, use early returns

### Task 4.16: Fix extraction_checker.py deep nesting

**Approach**: Extract validation steps, use guard clauses

### Task 4.18: Fix study_classifier.py deep nesting

**Approach**: Extract conditional logic into helper methods

---

## Testing Strategy (User-Approved)

### Integration Tests First
- **Before splitting**: Verify integration tests cover 2-3 representative PDFs end-to-end
- **During splitting**: Run integration suite after each file split
- **After splitting**: Add targeted unit tests ONLY for new helper methods with complex logic

### Don't Test Before Split
- Avoid duplicating effort testing monolith functions that will disappear
- Focus on black-box behavior, not structure

---

## Implementation Checklist

### Phase 4A: Magic Numbers (FIRST) ✅
- [ ] Create `core/constants.py`
- [ ] Update `core/config.py` with new fields
- [ ] Replace magic numbers in hierarchical_pipeline.py
- [ ] Replace magic numbers in extraction_checker.py
- [ ] Replace magic numbers in parser.py
- [ ] Replace magic numbers in extractor.py
- [ ] Replace magic numbers in remaining 11+ files
- [ ] Run integration tests after each file

### Phase 4B: Critical Path Splits
- [ ] Split hierarchical_pipeline.py → pipeline/
- [ ] Split extractor.py → extractors/
- [ ] Split extraction_checker.py → validation/
- [ ] Refactor batch_processor.py (extract ExecutionHandler, fix nesting)

### Phase 4C: Remaining Splits
- [ ] Split parser.py → parsers/
- [ ] Split binary_deriver.py → binary/
- [ ] Split relevance_classifier.py → classification/

### Phase 4D: Large Functions
- [ ] Extract service.py::run_extraction
- [ ] Extract extractor.py::extract_with_evidence

### Phase 4E: Deep Nesting
- [ ] Fix vectorizer.py
- [ ] Fix extraction_checker.py
- [ ] Fix study_classifier.py

---

## Success Criteria

1. ✅ All integration tests pass after each change
2. ✅ No files >400 lines
3. ✅ No functions >100 lines
4. ✅ No magic numbers (all in config.py or constants.py)
5. ✅ No deep nesting (max 3 levels)
6. ✅ No ambiguous variable names in critical path

---

## Estimated Timeline

- **Phase 4A**: 2 hours (magic numbers)
- **Phase 4B**: 12 hours (critical path splits)
- **Phase 4C**: 8 hours (remaining splits)
- **Phase 4D**: 6 hours (large functions)
- **Phase 4E**: 4 hours (deep nesting)

**Total**: ~32 hours (4 days of focused work)

---

## Risk Mitigation

1. **Integration tests** run after every file change
2. **Git commits** after each successful file split
3. **Composition pattern** reduces sync/async duplication risk
4. **Magic numbers first** makes all subsequent changes easier to read

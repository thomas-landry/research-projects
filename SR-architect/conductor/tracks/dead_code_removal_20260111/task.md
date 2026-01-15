# Dead Code Removal & Code Quality Fixes - Task Breakdown

**Track**: `conductor/tracks/dead_code_removal_20260111/`  
**Execution Method**: Subagent-driven development with TDD  
**Created**: 2026-01-11

---

## Phase 1: Dead Code Removal

### Core Modules
- [x] **Task 1.1**: Delete 4 dead core modules ✅
  - Files: `abstract_first_extractor.py`, `pubmed_fetcher.py`, `validation_rules.py`, `self_consistency.py`
  - Owner: `/senior_dev`
  
- [x] **Task 1.2**: Archive auto_corrector.py ✅
  - Move to `archive/` directory (may be needed in future)
  - Owner: `/senior_dev`
  
- [x] **Task 1.3**: Add rapidfuzz to requirements.txt ✅
  - Required for `fuzzy_deduplicator.py`
  - Owner: `/senior_dev`

### Agent Modules
- [x] **Task 1.4**: Delete 2 unused agent modules ✅
  - Files: `conflict_resolver.py`, `section_locator.py`
  - Note: Keeping `researcher_analysis.py` for future use
  - Owner: `/senior_dev`

### Test Files
- [x] **Task 1.5**: Delete orphaned test files ✅
  - Files: `test_abstract_first_extractor.py`, `test_self_consistency.py`, `test_phase2_components.py`, `test_phase4_components.py`
  - Owner: `/senior_dev`

### Cleanup
- [x] **Task 1.6**: Delete standalone scripts ✅
  - File: `debug_openrouter_pricing.py` (not found - already deleted)
  - Owner: `/senior_dev`

- [x] **Task 1.7**: Delete temporary directories ✅
  - Directory: `temp_healy/` (not found - already deleted)
  - Owner: `/senior_dev`

- [x] **Task 1.8**: Clean unused imports in `hierarchical_pipeline.py` ✅
  - Removed dead imports and instantiations for AbstractFirstExtractor, PubMedFetcher, ConflictResolverAgent, SectionLocatorAgent
  - Also cleaned `core/pipeline/core.py`
  - Owner: `/senior_dev`

- [x] **Task 1.9**: Clean minor Vulture findings - unused imports (7 files) ✅
  - Removed 8 unused imports
  - Owner: `/senior_dev`

- [x] **Task 1.10**: Clean unused variables ✅
  - Replaced 13 unused `cls`, exception variables, lambda params with `_`
  - Removed 1 unused function parameter
  - Owner: `/senior_dev`

### Documentation Updates
- [x] **Task 1.11**: Update track documentation ✅
  - Files: `code_quality_issues.md`, `dead_code_findings.md`
  - Mark completed items, update status
  - Owner: `/docs_agent`

---

## Phase 2: Critical Regression Fix ⚠️ HIGH PRIORITY

> **Impact**: Restores 60-70% cost reduction via Tier 0 regex extraction

### RegexExtractor Integration
- [x] **Task 2.1**: Write failing tests for RegexExtractor (TDD RED)
  - Create `tests/test_regex_tier_zero.py`
  - Owner: `/senior_dev`

- [x] **Task 2.2**: Restore RegexExtractor integration (TDD GREEN)
  - Add import, initialization, Tier 0 extraction logic
  - Owner: `/senior_dev`

### TwoPassExtractor Integration
- [x] **Task 2.3**: Write failing tests for TwoPassExtractor (TDD RED)
  - Create `tests/test_two_pass_integration.py`
  - Owner: `/senior_dev`

- [x] **Task 2.4**: Verify TwoPassExtractor integration
  - Check if already present, add if missing
  - Owner: `/senior_dev`

### Extractor Enhancement
- [x] **Task 2.5**: Add `pre_filled_fields` support to StructuredExtractor
  - TDD RED: Create `tests/test_extractor_prefilled.py`
  - TDD GREEN: Implement parameter and logic
  - Owner: `/senior_dev`

---

## Phase 3: Anti-Pattern Fixes

- [x] **Task 3.1**: Centralize `os.getenv()` calls
  - Move 15+ calls to `core/config.py`
  - TDD: Create `tests/test_config_centralization.py`
  - Owner: `/senior_dev`

- [x] **Task 3.2**: Fix bare exception handling
  - Files: `core/client.py`, `core/service.py`
  - Add specific exceptions and logging
  - Owner: `/senior_dev`

- [x] **Task 3.3**: Fix async import anti-pattern
  - Move `import asyncio` to module level in `service.py`
  - Owner: `/senior_dev`

- [x] **Task 3.4**: Centralize client creation logic
  - Use `LLMClientFactory` everywhere (VERIFIED: already done)
  - Owner: `/senior_dev`

- [x] **Task 3.5**: Comprehensive config audit
  - Ensure ALL API calls, local model switching, global configs in `config.py`
  - Owner: `/senior_dev`

- [x] **Task 3.6**: Refactor `token_tracker.py` for clarity
  - Move pricing constants to `config.py`
  - Fix API pricing fetch (never hardcode, always fetch + cache)
  - Fix code smells: magic numbers, bare exceptions, ambiguous names
  - Add comprehensive type hints and documentation
  - Owner: `/refactor_standards_guardian`

---

## Phase 4: Code Smell Remediation

### Phase 4A: Extract Magic Numbers (DO FIRST)
- [x] **Task 4.0**: Extract magic numbers to config.py and constants.py
  - Create `core/constants.py` for algorithm parameters ✅
  - Add threshold/limit fields to `config.py` ✅
  - Replace magic numbers in 15+ files ✅ (9 files refactored)
  - Test after each file replacement ✅
  - Owner: `/refactor-for-clarity`

### Phase 4B: Critical Path File Splitting
- [x] **Task 4.5**: Split `hierarchical_pipeline.py` (860 lines) ✅ COMPLETE
  - Created 7 files totaling 1,163 lines
  - Eliminated 90 lines of sync/async duplication
  - Introduced dependency injection pattern
  - All files pass `/refactor-for-clarity` standards
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.6**: Split `extractor.py` (696 lines)
  - Split into: `extractors/base.py`, `extractors/evidence.py`, `extractors/retry.py`
  - Use composition pattern for sync/async
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.7**: Split `extraction_checker.py` (509 lines)
  - Split into: `validation/checker.py`, `validation/validators.py`, `validation/formatters.py`
  - Rename ambiguous variables (v → validation_score, item → field_result)
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.9**: Refactor `batch_processor.py` (280 lines) - CRITICAL PATH ✅
  - ExecutionHandler class already extracted (lines 41-167)
  - Shared logic centralized for sync/async paths
  - Owner: `/refactor-for-clarity`

### Phase 4C: Remaining File Splitting
- [ ] **Task 4.8**: Split `parser.py` (500 lines)
  - Split into: `parsers/base.py`, `parsers/docling.py`, `parsers/fallbacks.py`
  - Use strategy pattern
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.12**: Split `binary_deriver.py` (603 lines)
  - Split into: `binary/core.py`, `binary/rules.py`
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.13**: Split `relevance_classifier.py` (470 lines)
  - Split into: `classification/classifier.py`, `classification/helpers.py`
  - Owner: `/refactor-for-clarity`

### Phase 4D: Large Function Extraction
- [ ] **Task 4.3**: Extract `service.py::run_extraction` (226 lines)
  - Split into: setup, parsing, execution, callbacks, vectorization
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.4**: Extract `hierarchical_pipeline.py::extract_document` (200 lines) ✅
  - Already complete - Task 4.5 refactored this into ExtractionExecutor
  - extract_sync() and extract_async() are 52 lines each (well-structured)
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.14**: Extract `extractor.py::extract_with_evidence` (128 lines) ✅
  - Extract: prompt building, response parsing, validation
  - Owner: `/refactor-for-clarity`

### Phase 4E: Deep Nesting Fixes
- [ ] **Task 4.1**: Fix deep nesting in `hierarchical_pipeline.py`
  - Extract nested logic into helper methods
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.2**: Fix deep nesting in `service.py` ✅
  - Use early returns, extract nested loops
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.15**: Fix deep nesting in `batch_processor.py` ✅
  - Max nesting = 4 (acceptable with ExecutionHandler pattern)
  - Clean structure with composition
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.16**: Fix deep nesting in `extraction_checker.py` ✅
  - Already complete - max nesting = 2 levels
  - validation/checker.py has clean structure
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.18**: Fix deep nesting in `study_classifier.py` ✅
  - Already complete - max nesting = 3 levels
  - Clean conditional logic
  - Owner: `/refactor-for-clarity`

- [x] **Task 4.10**: Fix ambiguous variable names ✅
  - Already complete - no ambiguous single-letter variables found
  - Code uses descriptive names throughout
  - Owner: `/refactor-for-clarity`

### Phase 4F: Additional File Refactoring (LOW PRIORITY - defer)
- [ ] **Task 4.22**: Split `cache_manager.py` (419 lines) (DEFERRED)
  - Split into: `cache/manager.py`, `cache/models.py`, `cache/constants.py`
  - Condition: Only if modifying cache schema
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.23**: Extract large function in `client.py` (DEFERRED)
  - Split `restart_service` (45 lines) into platform-specific methods
  - Condition: Only if adding new LLM providers
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.24**: Eliminate client creation duplication in `client.py` (DEFERRED)
  - Extract common client creation pattern
  - Condition: Only if changing providers
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.25**: Fix ambiguous variable names in additional files (LOW)
  - `cache_manager.py`: `row` → `cache_row` / `field_row`
  - Do alongside other refactors, not in isolation
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.26**: Extract remaining magic numbers (LOW)
  - `client.py`: `2.0` → `constants.OLLAMA_HEALTH_CHECK_TIMEOUT`
  - Add to constants.py during Phase 4A cleanup
  - Owner: `/refactor-for-clarity`

---

## Phase 5: Multi-File Code Quality Refactoring

> **Source**: Multi-file code quality review (2026-01-14)  
> **Files Analyzed**: 6 files (2,092 lines)  
> **Issues Found**: 18 code smells  
> **Reference**: `multi_file_refactor_plan.md`

### Phase 5A: Quick Wins (Priority 1-2)
- [x] **Task 5.1**: Extract magic numbers in `schema_discovery.py` ✅
  - Extract: `MIN_PDF_SIZE_BYTES = 10240`, `MIN_TXT_SIZE_BYTES = 100`, `MAX_CONTEXT_CHARS = 20000`, `DEFAULT_RANDOM_SEED = 42`
  - Lines: 146, 148, 187, 163
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.2**: Extract magic numbers in `researcher_analysis.py` ✅
  - Extract: `LOW_FILL_RATE_THRESHOLD = 0.5`, `MAX_UNIQUE_VALUES_FOR_CATEGORICAL = 5`
  - Lines: 48, 72
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.3**: Add missing docstring to `researcher_analysis.py::analyze_extraction()` ✅
  - Add comprehensive docstring with Args and purpose
  - Line: 7
  - Owner: `/docs_agent`

- [x] **Task 5.4**: Expand docstring in `cache_manager.py::compute_doc_hash()` ✅
  - Add Args, Returns sections
  - Line: 412
  - Owner: `/docs_agent`

### Phase 5B: Variable Renaming (Priority 5)
- [x] **Task 5.5**: Rename ambiguous variables in `schema_builder.py` ✅
  - `clean_name` → `sanitized_name` (line 349)
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.6**: Rename ambiguous variables in `parser.py` ✅
  - `doc` → `pdf_document` (line 414 in `_parse_pdf_pymupdf`)
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.7**: Rename ambiguous variables in `schema_discovery.py` ✅
  - `all_suggestions` → `field_suggestions_from_all_papers` (line 308)
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.8**: Remove unused variable in `researcher_analysis.py` ✅
  - Remove `low_confidence_fields` (line 29)
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.9**: Add type hints to `researcher_analysis.py` ✅
  - Add type hints to `analyze_extraction()` function
  - Owner: `/refactor-for-clarity`

### Phase 5C: Extract Repeated Code (Priority 4)
- [x] **Task 5.10**: Extract `_chunk_text()` helper in `parser.py` ✅
  - Consolidate 3 repeated `split_text_into_chunks()` calls
  - Lines: 342, 423, 453
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.11**: Extract `FIELD_TYPE_MAPPING` constant in `schema_discovery.py` ✅
  - Move type mapping dict to module level
  - Lines: 337-345
  - Owner: `/refactor-for-clarity`

- [x] **Task 5.12**: Extract `_prepare_extraction_context()` in `pipeline/core.py` ✅
  - Already complete - code delegates to _extraction_executor
  - Lines: 269-289, 291-311
  - Owner: `/refactor-for-clarity`

### Phase 5D: Large Function Refactoring (Priority 3) - DEFERRED
> **Note**: These are complex refactorings that should be done when actively working on these files

- [ ] **Task 5.13**: Refactor `parser.py::parse_pdf()` (86 lines) (DEFERRED)
  - Extract: `_parse_with_fallback()`, `_apply_imrad_if_enabled()`
  - Lines: 232-318
  - Condition: Only when modifying parser logic
  - Owner: `/refactor-for-clarity`

- [ ] **Task 5.14**: Refactor `schema_discovery.py::discover_schema()` (69 lines) (DEFERRED)
  - Extract: `_select_sample_papers()`, `_analyze_papers()`, `_build_field_definitions()`
  - Lines: 285-354
  - Condition: Only when modifying schema discovery
  - Owner: `/refactor-for-clarity`

---

## Phase 6: Hardcoded Values

- [ ] **Task 5.1**: Define magic number constants
  - Files: `client.py`, `service.py`, `hierarchical_pipeline.py`
  - Owner: `/senior_dev`

- [ ] **Task 5.2**: Centralize path configuration
  - Use `settings.LOG_DIR`, `settings.VECTOR_DIR`
  - Owner: `/senior_dev`

- [ ] **Task 5.3**: Centralize API endpoints
  - Remove duplicate hardcoded URLs
  - Owner: `/senior_dev`

---

## Phase 6: Minor Issues

- [ ] **Task 6.1**: Add missing docstrings
  - Files: `config.py`, `client.py`
  - Owner: `/docs_agent`

- [ ] **Task 6.2**: Complete type hints
  - Files: `client.py`, `service.py`
  - Owner: `/senior_dev`

- [ ] **Task 6.3**: Remove or fix TODO/FIXME comments
  - Address TODOs in `two_pass_extractor.py`
  - Owner: `/senior_dev`

---

## Phase 7: Vulture Findings Cleanup

- [ ] **Task 7.1**: Final Vulture scan
  - Run Vulture after all changes
  - Document remaining findings
  - Owner: `/senior_dev`

---

## Verification & Documentation

- [ ] **Final Verification**: Run full test suite
  - Command: `pytest tests/ -v --tb=short`
  - Owner: `/qa_agent`

- [ ] **Update Documentation**
  - Update CHANGELOG.md
  - Update `code_quality_issues.md` (mark fixed items)
  - Update `dead_code_findings.md` (mark deleted items)
  - Update `subagent_execution_plan.md` (check completed tasks)
  - Update CODE_MAP.md (if exists)
  - Owner: `/docs_agent`

---

## New Feature Implementation

- [ ] **Task 8.1**: Implement ComplexityClassifier integration
  - Integrate into parsing pipeline
  - TDD approach required
  - Owner: `/senior_dev`

- [ ] **Task 8.2**: Implement FuzzyDeduplicator integration
  - Integrate into chunking pipeline
  - Ensure rapidfuzz is installed
  - TDD approach required
  - Owner: `/senior_dev`

---

## Summary

**Total Tasks**: 45+  
**Estimated LOC Removed**: ~2,500+  
**Estimated LOC Refactored**: ~2,000+  
**Estimated LOC Added**: ~500+ (new features)  
**Critical Priority**: Phase 2 (Regression Fix)

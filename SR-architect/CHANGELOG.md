# Changelog

All notable changes to the SR-Architect project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Memory Profiler**: New `tests/profile_memory.py` using `tracemalloc` for baseline tracking.
- **Cache Eviction**: LRU cache eviction in `DocumentParser` (max 100 entries).
- **ChromaDB Cleanup**: `close()` method and context manager for `ChromaVectorStore`.
- **Session Reuse**: `requests.Session()` in `PubMedFetcher` for connection pooling.

### Changed
- **Refactored**: Extracted `_filter_and_classify()` and `_apply_audit_penalty()` helpers in `HierarchicalExtractionPipeline`.

### Known Issues
- **TEST-001**: `test_settings_defaults` fails - WORKERS config expected 1, actual 4.
- **TEST-002**: `test_fetch_by_pmid_not_found` fails - cache returns object instead of None.

## [1.0.0] - 2026-01-05

### Added
- **Hierarchical Extraction**: New pipeline utilizing Docling, PICO screening, and multi-stage verification.
- **Adaptive Schema Discovery**: `discover` command to auto-generate extraction schemas from sample papers.
- **Benchmarking Tools**: `benchmark` command to test extraction accuracy across local models.
- **CLI Enhancements**: New flags `--hierarchical`, `--theme`, `--resume`.
- **Audit Logging**: Comprehensive JSONL logging for every extraction step.

### Fixed
- **BUG-001**: Fixed index out of bounds error in parser when headings list is empty.
- **BUG-002**: Resolved issue where empty context extracted zero chunks.
- **BUG-003**: Fixed division by zero error in relevance classifier when confidence is None.
- **BUG-004**: Added sanitization for control characters in metadata to prevent ChromaDB errors.
- **BUG-005**: Implemented path traversal protection for malicious filenames.
- **BUG-006**: Defaulted missing chunk section attributes to "Uncategorized" to prevent null errors.
- **BUG-007**: Improved PDF parsing robustness for edge cases (scanned columns).
- **BUG-008**: Fixed schema field collision by prefixing internal metadata fields with `__pipeline_`.
- **BUG-010**: Added handling for evidence truncation warning in Extractor (max 15k chars).
- **BUG-011**: Fixed `AttributeError` on `DocMeta` object access.

### Changed
- Standardized logging across all modules (replaced `print` with `logger`).
- Refactored `HierarchicalExtractionPipeline` for better state management.

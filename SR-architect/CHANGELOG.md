# Changelog

All notable changes to the SR-Architect project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

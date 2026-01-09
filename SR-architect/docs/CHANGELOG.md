# Changelog

All notable changes to the SR-architect project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **CSV Schema Inference**: Automatically generate extraction schemas from CSV templates (`--schema template.csv`).
- **Model Aliases**: Easy switching with `--model gemini`, `--model sonnet`, `--model llama3`.
- **Cost Optimization**: Defaulted to `google/gemini-2.0-flash-lite-001` for 95% cost reduction.
- **Excellence-Focused Integration (Phase A & B)**
    - **Fuzzy Quote Validation (`core/text_utils.py`)**: Added Jaccard similarity scoring to robustly validate quotes, preventing "hallucination" flags for minor punctuation differences.
    - **Unit-Context Extraction (`core/sentence_extractor.py`)**: New extractor class that processes text sentence-by-sentence with sliding windows to improve recall for complex fields.
    - **Hybrid Pipeline Integration**: `HierarchicalExtractionPipeline` now supports a hybrid mode that runs `SentenceExtractor` in parallel for specific complex fields (e.g., `histopathology`).
    - **Recall Boost (Phase C)**: Implemented "review loop" in pipeline that detects missing fields and re-prompts the LLM specifically for them, improving recall for sparse data.
    - **Tests**: Added `tests/test_sentence_extractor.py`, `tests/test_pipeline_integration.py`, and `tests/test_recall_boost.py`.

### Changed
- **QualityAuditorAgent**: Updated to use deterministic fuzzy matching for quote verification before falling back to LLM, saving tokens and improving accuracy.
- **HierarchicalExtractionPipeline**: Updated `extract_document_async` to support parallel hybrid extraction strategies.

### Fixed
- **NLTK Dependency**: Added robust fallback to regex tokenization if NLTK data is missing.
- **Limit Flag**: Fixed CLI limit flag handling (previous session).

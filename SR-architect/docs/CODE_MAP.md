# SR-Architect Code Map

This document maps the codebase structure, defining the role of each component and its active status. Use this to quickly understand dependencies and identify dead code.

## 🟢 Active Core (The Engine)
These files are the foundation of the extraction and review pipelines.

| File | Role | Dependencies |
|------|------|--------------|
| `core/pipeline/core.py` | **Main Extraction Engine**. Orchestrates filtering, classification, extraction, validation. | `utils`, `extractor`, `checker`, `filter` |
| `core/pipeline/extraction/executor.py` | **Extraction Logic**. Handles hybrid extraction and validation loops. | `checker`, `extractor` |
| `core/batch/handler.py` | **Parallel Executor**. Handles threading and state updates for batch jobs. | `state_manager`, `pipeline` |
| `core/extractors/structured.py` | **LLM Interface**. Wraps Instructor for structured output. | `utils`, `token_tracker` |
| `core/validation/checker.py` | **LLM Validator**. Checks accuracy/consistency of extractions. | `extractor`, `utils` |
| `core/state_manager.py` | **Persistence**. JSON/Pydantic state for extraction jobs. | |
| `core/prisma_state.py` | **Domain Model**. TypedDicts/Enums for PRISMA compliance. | |
| `core/utils.py` | **Utilities**. Shared `load_env`, `make_request`, logging. | |
| `core/complexity_classifier.py` | **Adaptive Logic**. Routes simple/complex docs to appropriate parsers. | `utils` |
| `core/fuzzy_deduplicator.py` | **Deduplication**. Removes near-duplicate text/chunks. | `config` |
| `core/cache/manager.py` | **Cache Manager**. File-based caching for API responses. | `core.cache.models` |
| `core/platform_utils.py` | **Platform Ops**. Service management (Ollama) & system checks. | |

## 🔵 Active Agents (The Workers)
These files are the foundation of the extraction and review pipelines.

| File | Role | Status |
|------|------|--------|
| `agents/orchestrator_pi.py` | **Review Orchestrator**. Manages the full PRISMA lifecycle (search -> screen). | Active (for `prisma_cli.py`) |
| `agents/librarian.py` | **Search Agent**. Queries PubMed API. | Active |
| `agents/screener.py` | **Screening Agent**. TF-IDF + LLM abstract screening. | Active |
| `agents/quality_auditor.py` | **Audit Agent**. Sample checking. | Active |
| `agents/schema_discovery.py` | **Discovery Agent**. Analyzes papers to suggest schemas. | Active (`cli.py discover`) |
| `agents/synthesizer.py` | **Reporting Agent**. Generates text/summaries. | Active |

## 🟣 CLI & Entry Points
| File | Role |
|------|------|
| `cli.py` | **Data Extraction Tool**. Focused on PDF -> CSV/JSON. Uses `core/`. |
| `prisma_cli.py` | **Systematic Review Tool**. Focused on PRISMA workflow. Uses `agents/`. |

## 🟡 Support & Utilities (Active)
| File | Role |
|------|------|
| `core/token_tracker.py` | Cost estimation and token counting. |
| `core/content_filter.py` | Removes refs/affiliations to save tokens. |
| `core/schema_builder.py` | Dynamic Pydantic models for user schemas. |
| `core/vectorizer.py` | ChromaDB wrapper for semantic search. |
| `core/audit_logger.py` | Structured logging for audits. |
| `core/parsers/docling.py` | PDF parsing strategy (Docling). |
| `core/parsers/fallbacks.py` | Fallback parsers (PyMuPDF). |

## 🔴 Dead Code (To Be Removed)
| File | Reason | LOC | Action |
|------|--------|-----|--------|
| `core/hierarchical_pipeline.py` | **Splitted & Removed** | - | - |
| `core/parser.py` | **Splitted & Removed** | - | - |
| `core/binary_deriver.py` | **Splitted & Removed** | - | - |
| `core/relevance_classifier.py` | **Splitted & Removed** | - | - |
| `core/extractors.py` | **Splitted & Removed** | - | - |

**Total**: 11 files, ~3,900 LOC

## ✅ Resolved Issues
| File | Status | Issue | Action |
|------|--------|-------|--------|
| `core/regex_extractor.py` | ✅ Working | Integration Restored | - |
| `core/two_pass_extractor.py` | ✅ Working | Integration Restored | - |
| `tests/test_pipeline.py` | ✅ Passing | Retry Loop Test Fixed | - |

## ⚪️ Future / Experimental (Inactive but Valuable)
| File | Role | Recommendation |
|------|------|----------------|
| `core/study_classifier.py` | Classifies study types (RCT vs Case Series). Not currently wired. | **Keep**. Use in future adaptive pipeline. |
| `core/binary_deriver.py` | Derives binary flags from text (specific domain rules). | **Keep**. Specific business logic. |
| `agents/meta_analyst.py` | Statistical analysis agent. | **Keep**. Future feature. |
| `agents/conflict_resolver.py` | Resolves screening disagreements. | **Keep**. Future feature. |
| `agents/section_locator.py` | Locates specific sections. | **Keep**. Future feature. |

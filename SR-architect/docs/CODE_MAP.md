# SR-Architect Code Map

This document maps the codebase structure, defining the role of each component and its active status. Use this to quickly understand dependencies and identify dead code.

## 🟢 Active Core (The Engine)
These files are the foundation of the extraction and review pipelines.

| File | Role | Dependencies |
|------|------|--------------|
| `core/hierarchical_pipeline.py` | **Main Extraction Engine**. Orchestrates filtering, classification, extraction, validation. | `utils`, `extractor`, `checker`, `filter` |
| `core/batch_processor.py` | **Parallel Executor**. Handles threading and state updates for batch jobs. | `state_manager`, `hierarchical_pipeline` |
| `core/extractor.py` | **LLM Interface**. Wraps Instructor for structured output. | `utils`, `token_tracker` |
| `core/validator.py` | **Validation Logic**. (Check if this exists or is `extraction_checker.py`) | |
| `core/extraction_checker.py` | **LLM Validator**. checks accuracy/consistency of extractions. | `extractor`, `utils` |
| `core/state_manager.py` | **Persistence**. JSON/Pydantic state for extraction jobs. | |
| `core/prisma_state.py` | **Domain Model**. TypedDicts/Enums for PRISMA compliance. | |
| `core/utils.py` | **Utilities**. Shared `load_env`, `make_request`, logging. | |

## 🔵 Active Agents (The Workers)
Autonomous agents performing specific lifecycle tasks.

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
| `core/parser.py` | PDF parsing (Docling/PyMuPDF). |

## 🔴 Deprecated / Redundant (Candidates for Deletion)
| File | Reason for Deprecation | Replacement |
|------|------------------------|-------------|
| `core/extraction_orchestrator.py` | Superseded by `HierarchicalExtractionPipeline` + `cli.py` logic. | `cli.py` / `batch_processor.py` |
| `core/confidence_router.py` | Superseded by LLM-based `ExtractionChecker`. | `core/extraction_checker.py` |
| `agents/multi_agent.py` | Empty stubs / unused code. | N/A |

## ⚪️ Future / Experimental (Inactive but Valuable)
| File | Role | Recommendation |
|------|------|----------------|
| `core/study_classifier.py` | Classifies study types (RCT vs Case Series). Not currently wired. | **Keep**. Use in future adaptive pipeline. |
| `core/binary_deriver.py` | Derives binary flags from text (specific domain rules). | **Keep**. Specific business logic. |
| `agents/meta_analyst.py` | Statistical analysis agent. | **Keep**. Future feature. |
| `agents/conflict_resolver.py` | Resolves screening disagreements. | **Keep**. Future feature. |
| `agents/section_locator.py` | Locates specific sections. | **Keep**. Future feature. |

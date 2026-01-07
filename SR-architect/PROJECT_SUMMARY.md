# SR-Architect Project Overview

## 1. Project Mission
**SR-Architect** is an agentic ETL (Extract, Transform, Load) pipeline designed to automate data extraction for systematic reviews. It transforms unstructured PDF research papers into structured, clinically validated datasets (CSV) with audit trails and semantic querying capabilities.

## 2. Architecture & Framework
- **Language**: Python 3.10+
- **Core Framework**: Custom Agentic Pipeline (inspired by LangChain/Instructor concepts but built lightweight)
- **Data Engineering**: Pydantic (validation), Tenacity (retries)
- **PDF Parsing**: Docling (IBM) → PyMuPDF (fallback) → pdfplumber (tertiary)
- **LLM Integration**: Instructor (structured output), LiteLLM/OpenAI/Ollama adapters
- **Vector Store**: ChromaDB (semantic search/RAG)
- **CLI**: Typer + Rich (interactive terminal UI)

### Key Components
1.  **DocumentParser**: Intelligent multi-stage parser with OCR, table extraction, and complexity classification.
2.  **HierarchicalExtractionPipeline**:
    *   **Phase 1 (Filter)**: Heuristic + LLM filtering to remove non-relevant sections (refs, acknowledgments).
    *   **Phase 2 (Relevant)**: `RelevanceClassifier` identifies chunks matching the extraction theme.
    *   **Phase 3 (Extract)**: `Extractor` uses Pydantic schemas to pull structured data with evidence quotes.
    *   **Phase 4 (Verify)**: `ExtractionChecker` (Reflection) validates extractions against quotes and theme.
3.  **Agents**:
    *   `SchemaDiscoveryAgent`: Adapts schema to new domains automatically.
    *   `QualityAuditorAgent`: Reviews extraction quality.
4.  **Local LLM Support**: Fully compatible with Ollama (Llama 3, Mistral, Qwen) via custom `OllamaClient` with health checks.

## 3. Implemented Features
- **Intelligent Parsing**:
    - Complexity classification (Simple/Medium/Complex) checks layout.
    - Layout cleaning (removes headers/footers/watermarks).
    - IMRAD section detection (Introduction, Methods, Results, Discussion).
- **Robust Extraction**:
    - Self-correcting feedback loop (Checker validation).
    - Source provenance (every value linked to an exact quote).
- **Optimization**:
    - Token tracking & cost estimation.
    - Logic-based filtering (regex/heuristics) to save tokens.
    - Caching (Parsed docs, PubMed metadata).
- **Benchmarking**:
    - Automated model comparison harness.
    - Comprehensive accuracy evaluation (Exact/KeyTerms/Semantic metrics).

## 4. Current Benchmarks (Jan 2026)
*Test Set: 3 challenging case report PDFs (Virk 2023, Kuroki 2002, Luvison 2013)*

| Model | Provider | Time (s) | CAS Score* | Cost | Notes |
|-------|----------|----------|------------|------|-------|
| **Claude 3.5 Sonnet** | OpenRouter | **100s** | **0.69** | $ | Gold standard accuracy. 4x faster than local. |
| **Llama 3.1 8B** | Ollama | 389s | 0.50 | FREE | Best local model accuracy. Slow. |
| **Mistral (latest)** | Ollama | 585s | 0.35 | FREE | Very slow. Lower accuracy. |
| **Qwen 2.5 Coder** | Ollama | 415s | 0.34 | FREE | struggling with semantic nuance. |

> **CAS (Clinical Accuracy Score)**: Weighted metric prioritizing critical fields (Histopathology, Age, Sex).
> - Sonnet: ~70-90% semantic match rate.
> - Local LLMs: ~20-50% semantic match rate.

## 5. Goals for Experts
We need to optimize the pipeline to bridge the gap between Local LLMs and SOTA Cloud LLMs.

**Detailed Objectives:**
1.  **Speed**: Decrease processing time for local LLMs (target: <200s/paper).
2.  **Accuracy**: Improve Local LLM CAS score to >0.60.
3.  **Token Usage**: Reduce context window usage to prevent truncation and lower costs/latency.

**Ideas for Improvement:**
- **Advanced Chunking**: Move beyond recursive splitting to semantic/propositional chunking?
- **Guided Sampling**: Use small models to identify *only* the specific sentences needed, then pass *only* those to the extractor?
- **Speculative Decoding**: (If applicable locally)
- **Constrained Decoding**: Force specific JSON schemas more strictly (already using Instructor, but maybe grammars?)
- **Fine-tuning**: Fine-tune a small Llama/Mistral adapter specifically for "Medical Case Report Extraction"?

## 6. Planned/In-Progress
- Integration of `SemanticChunker` (Prototype done).
- `FuzzyDeduplicator` implementation (Prototype done).

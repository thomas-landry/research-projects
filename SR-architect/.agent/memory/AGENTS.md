# SR-Architect Agent Context

## Project Identity

SR-Architect is an **Agentic ETL pipeline** for systematic review data extraction. It transforms screened PDFs into analysis-ready structured data with near-100% accuracy and full audit trails.

## Multi-Agent Architecture

| Agent | Role | Location |
|-------|------|----------|
| **Screener** | Intelligent inclusion/exclusion via PICO criteria | `agents/screener.py` |
| **Extractor** | Structured data extraction with self-proving quotes | `core/extractor.py` |
| **Auditor** | Validates extractions against source text | `core/extraction_checker.py` |
| **Synthesizer** | Aggregates data into meta-analysis reports | `agents/synthesizer.py` |
| **Senior Dev** | Bug remediation, code fixes, refactoring | `.agent/workflows/senior_dev.md` |
| **Orchestrator** | Task routing and multi-agent coordination | `.agent/workflows/orchestrator.md` |
| **QA Agent** | Test validation and coverage reporting | `.agent/workflows/qa_agent.md` |
| **Docs Agent** | Technical documentation | `.agent/workflows/docs_agent.md` |

## Pipeline Flow

```
PDF → Docling Parser → Chunks → Relevance Filter → Extractor → Auditor → CSV
                                      ↓
                              ChromaDB (vectors)
```

## Key Architectural Decisions

1. **Self-Proving Extractions**: Every extracted field requires a `_quote` with verbatim source text for verification.
2. **Retry Loop**: Max 3 iterations with revision prompts when validation fails.
3. **Audit Trail**: All operations logged to JSONL for reproducibility.
4. **Context Limits**: Chunks truncated to 15,000 characters to respect LLM context windows.

## Tech Stack Rationale

| Choice | Reason |
|--------|--------|
| Docling | Best academic PDF parser (handles multi-column, tables) |
| Instructor | Type-safe structured outputs via Pydantic |
| ChromaDB | Portable vector store with persistence |
| Typer/Rich | Beautiful CLI with progress bars and tables |

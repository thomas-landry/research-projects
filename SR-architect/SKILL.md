---
description: "Systematic review data extraction pipeline with RAG and structured LLM outputs"
version: "1.0.0"
dependencies:
  - docling
  - instructor
  - chromadb
  - typer
  - rich
  - pandas
---

# SR-Architect

Agentic ETL pipeline for extracting structured data from screened PDFs in systematic reviews and meta-analyses.

## Development Environment Rules

- **Python Version**: 3.10+
- **Package Management**: NEVER use `pip` directly. ALWAYS use `python3 -m pip` or `pip3` to ensure the correct environment is targeted.
    - ✅ `python3 -m pip install -r requirements.txt`
    - ❌ `pip install ...`
- **Testing**: Run tests with `pytest`.


## Capabilities

- **PDF Parsing**: Multi-column academic layouts, table extraction via Docling
- **Dynamic Schemas**: Define extraction variables at runtime or use presets
- **Structured Extraction**: LLM-powered extraction with Pydantic validation
- **Citation Traceability**: Every value includes source quote for verification
- **Semantic Search**: ChromaDB vector store for corpus-wide queries
- **Audit Logging**: Full provenance for reproducibility

## Quick Commands

```bash
# Extract from PDFs
python cli.py extract ./papers --schema case_report -o results.csv

# Interactive schema builder
python cli.py extract ./papers --interactive

# Semantic search
python cli.py query "treatment outcomes"

# Generate methods text
python cli.py methods
```

## Predefined Schemas

| Schema | Use Case |
|--------|----------|
| `case_report` | Case reports, case series |
| `rct` | Randomized controlled trials |
| `observational` | Cohort, case-control studies |

## Integration with Antigravity

Use Antigravity as the orchestrator:

1. "Extract data from the DPM papers using the case_report schema"
2. "Query the vector store for papers discussing histopathology"
3. "Generate the methods section for our extraction"

Antigravity will invoke the CLI commands and interpret results.

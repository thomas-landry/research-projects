# Tech Stack: SR-Architect

## Core Technologies
*   **Language:** Python
    *   *Rationale:* Primary language for data science, NLP, and AI orchestration.
*   **CLI Framework:** Typer
    *   *Rationale:* Provides a modern, type-safe way to build interactive CLI applications.
*   **UI/Visuals:** Rich
    *   *Rationale:* Enhances the CLI with tables, progress bars, and formatted output.

## AI & Data Extraction
*   **Structured Output:** Instructor (with Pydantic)
    *   *Rationale:* Ensures LLM outputs conform to strictly typed schemas with validation.
*   **Multi-Format Parsing:** Docling (IBM) + Text
    *   *Rationale:* High-fidelity parsing of academic PDFs and flexible support for plain text files.
*   **LLM Orchestration:** Custom Agentic Workflow
    *   *Rationale:* specialized agents (Screener, Extractor, Auditor) for high-accuracy evidence synthesis.
*   **Extraction API:** ExtractionService
    *   *Rationale:* High-level Python API that encapsulates the entire pipeline for modularity and easy integration.

## Data & Storage
*   **Vector Store:** ChromaDB
    *   *Rationale:* Lightweight, portable vector database for semantic search and RAG.
*   **Data Processing:** Pandas
    *   *Rationale:* Industry-standard tool for handling and exporting structured data to CSV.

## Infrastructure & Tooling
*   **Environment Management:** python-dotenv
*   **Quality Assurance:** Pytest (inferred from `pytest.ini`)

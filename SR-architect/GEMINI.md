# SR-Architect Project Context

## Project Overview
SR-Architect is an agentic ETL pipeline designed to automate data extraction for systematic reviews. It transforms screened PDFs into structured data (CSV) with audit trails and semantic querying capabilities.

## Key Goals
1.  **Automate Extraction:** Convert unstructured PDF text into structured data using LLMs.
2.  **Ensure Accuracy:** Provide source quotes for verification (self-proving extraction).
3.  **Scalability:** Handle 50+ papers efficiently.
4.  **Auditability:** Log every step and decision for scientific reproducibility.

## Architecture
-   **Parser:** Docling (IBM) for PDF parsing.
-   **Extractor:** Instructor (Pydantic + LLMs) for structured output.
-   **Storage:** ChromaDB for vector embeddings and semantic search.
-   **Interface:** CLI (Typer) for user interaction.

## Current Status
-   Core pipeline implemented (Parsing -> Screening -> Extraction).
-   Interactive schema builder available.
-   Initial pilot extraction on DPM papers successful.

## Memory
-   (Conductor will manage this section)

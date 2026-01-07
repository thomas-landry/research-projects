# Track Spec: Token Optimization & Hybrid Local/Cloud Architecture

## 1. Overview
This track aims to drastically reduce API costs and improve efficiency by implementing a "Hybrid Intelligence" pipeline. We will leverage the user's M4 Macbook Pro (24GB RAM) to offload tasks to local LLMs (Ollama) and optimize every stage of the ETL pipeline—from intelligent parsing to cascaded extraction. The goal is to only use expensive models (Sonnet) when absolutely necessary.

## 2. Core Strategies

### 2.1 Intelligent PDF Parsing & Pre-Processing (Non-LLM)
*   **Layout-Aware Cleaning:** Implement strict cleaning to handle column breaks, hyphenation, and headers/footers to prevent token fragmentation.
*   **Heuristic Routing:** Use `PyMuPDF` to classify page complexity. Route simple text pages to fast parsers and only complex/scanned pages to heavy OCR/Vision models.
*   **Section Filtering:** Identify and discard "References," "Acknowledgments," and "Appendices" before tokenization.
*   **Boilerplate Removal:** Strip recurring publisher metadata, copyright notices, and non-semantic artifacts.
*   **Explicit PyMuPDF Metrics:** Define complexity triggers based on image density (>30%), embedded tables, and multi-column layouts.
*   **Fallback Strategy:** Define a clear chain: Docling -> PyMuPDF4LLM -> Vision API.
*   **Metadata Integration:** Leverage PDF metadata/DOI to pre-fetch structured abstracts from PubMed where possible.

### 2.2 Advanced Chunking & Retrieval (Local LLM)
*   **Semantic Chunking:** Replace simple character splitting with semantic chunking (possibly via LangChain integration) to keep related concepts together.
*   **Hierarchical Indexing:** Create a two-tiered index. First, retrieval finds the relevant *section* (e.g., "Methods"), then precise chunking retrieves the specific paragraph.
*   **Deduplication:** Implement fuzzy deduplication to remove identical text blocks.
*   **Prompt Compression:** Use semantic compression (summarization) rather than simple lexical stripping to preserve medical context.

### 2.3 Hybrid Extraction Pipeline (Local -> Cloud)
*   **Model Cascading:**
    1.  **Tier 0 (Regex/Heuristic):** Bypass LLM for trivial fields (DOI, Year, Journal).
    2.  **Tier 1 (Local):** Attempt extraction using a local Ollama model (Llama 3.1 8B, Qwen2.5 7B, or Mistral 7B).
    3.  **Validation:** Run the `ExtractionChecker`.
        *   Confidence > 0.9 & Schema Valid -> ACCEPT
        *   Confidence 0.7-0.9 -> Escalate to Tier 2
        *   Confidence < 0.7 -> Escalate to Tier 3
    4.  **Tier 2 (Cloud - Cheap):** If local fails, try `gpt-4o-mini`.
    5.  **Tier 3 (Cloud - Expensive):** Only escalate to `claude-3.5-sonnet` if simpler models fail or for "High Complexity" fields.
*   **Complexity Definitions:**
    *   **Simple Fields:** Author, Year, Journal (Tier 0/1).
    *   **Numeric Fields:** Sample size, p-values (Tier 1 + Self-consistency).
    *   **High Complexity:** Interpretation of figures, nested data structures, ambiguous terminology (Tier 2/3).
*   **Self-Consistency:** For critical numeric fields, run the local model 3x and take the majority vote.
*   **Error Handling:** Implement a manual review queue for papers where all 3 tiers fail.

### 2.4 Caching & Efficiency
*   **Granular Caching:** Cache extraction results at the *field* level (Key: DocHash + FieldName + SchemaVersion).
*   **Parallel Batching:** Ensure `max_workers` logic supports running independent local tasks in parallel without choking the M4 chip.
*   **Invalidation Rules:** Trigger re-extraction only for specific fields when confidence drops below threshold or schema version increments.

## 3. Technical Constraints & Resource Management
*   **M4 Resource Management:**
    *   **RAM Ceiling:** 18GB (leaving ~6GB for macOS).
    *   **Throttling:** Start reducing `max_workers` at 14GB usage.
    *   **Workers:** Dynamic cap of 4-6 based on load.
*   **Model Selection:** Default to Llama 3.1 8B, but support Qwen2.5 7B and Mistral 7B for benchmarking.
*   **Monitoring:** Track tokens/cost per tier, failure modes, and OOM events.

## 4. Success Criteria
*   **Cost Reduction:** Achieve >50% reduction in Cloud API costs compared to the current baseline.
*   **Local Utilization:** Successfully run at least 40% of extraction tasks locally on the M4.
*   **Accuracy:** Maintain accuracy (F1 delta < 2%) compared to the Sonnet-only baseline.
*   **Latency:** Total pipeline time per paper should not increase by more than 20%.
*   **Maintainability:** Pipeline changes require <4 hours to implement and test.

## 5. Out of Scope
*   Fine-tuning local models.
*   Building a custom PDF parser from scratch.

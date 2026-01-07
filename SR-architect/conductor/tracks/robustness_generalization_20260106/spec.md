# Track Spec: Robustness & Generalization — Adaptive Schema Discovery & Interactive Polish

## 1. Overview
This track focuses on evolving SR-Architect from a static extraction tool into an intelligent, adaptive discovery platform. It implements "Adaptive Schema Discovery" to help researchers find hidden variables in their literature and polishes the interactive CLI experience to be more robust and user-friendly.

## 2. Requirements

### 2.1 Adaptive Schema Discovery
*   **Discovery Engine:** Implement a new agent/module that can take a sample of PDFs (e.g., 3-5 papers) and identify recurring data points or unique findings that aren't defined in the active schema.
*   **Suggestion Logic:** Present discovered fields to the user with descriptions and suggested data types.
*   **Schema Integration:** Allow the user to "accept" suggestions to automatically append them to their current extraction schema.

### 2.2 Interactive CLI Polish
*   **Safety Prompts:** Add confirmation dialogs for destructive or heavy-token operations (e.g., full extraction on 50+ papers).
*   **Undo Support:** In the interactive schema builder, allow users to go back or delete the last added field.
*   **Error Legibility:** Use `rich` panels to display extraction errors in a way that highlights *why* it failed (e.g., "Insufficient text extracted" vs "LLM Validation failed").

### 2.3 Internal Robustness
*   **Dual-Layer Logging:** Ensure `logs/sr_architect.log` captures full debug-level details while the console remains clean.
*   **API Layering:** Refactor the `extract` logic in `cli.py` and `HierarchicalExtractionPipeline` to ensure all core functionality is exposed via a stable Python API, paving the way for a future GUI.

### 2.4 Generalization
*   **Multi-Domain Validation:** Test the adaptive discovery on a non-DPM dataset to ensure it generalizes to other medical or scientific domains.

## 3. Success Criteria
*   Successfully discovery 3+ new relevant fields from a sample of 5 papers.
*   Zero crashes during a 10-paper extraction with "Adaptive" mode enabled.
*   User can "undo" a field addition in the interactive schema builder.
*   Verified debug logs captured in a file during a run.

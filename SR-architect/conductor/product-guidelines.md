# Product Guidelines: SR-Architect

## 1. Design Philosophy
*   **"Batteries Included":** The system must provide immediate value out of the box. Users should be able to run an extraction using sensible defaults (e.g., predefined schemas for common study types) without requiring extensive initial configuration.
*   **Transparency First:** The User Interface must demystify the "AI black box." Real-time feedback via progress bars, token usage statistics, and visible agent decisions is essential to build user trust in the automation.
*   **Fail-Safe & Resilient:** The pipeline must be robust. Errors in processing individual files (e.g., a corrupted PDF) must be handled gracefully—logged for review—without interrupting the broader batch extraction job.
*   **Debug-Ready:** While the user experience is clean, the system must maintain a comprehensive, "behind-the-scenes" logging infrastructure. All internal states, API responses, and errors must be captured to facilitate easy debugging and root-cause analysis without cluttering the main console.

## 2. Code & Quality Standards
*   **Self-Documenting Code:** Strict adherence to Python type hinting and comprehensive docstrings is required for all functions and classes. This ensures the codebase remains maintainable and supports auto-generated documentation.
*   **Modular Architecture:** The system must be built on a loosely coupled architecture. Core components—Parser, Extractor, Vector Store—must be designed as interchangeable modules, allowing for easy upgrades (e.g., swapping LLM providers) without system-wide refactoring.
*   **Comprehensive Logging:** Implement a dual-layer logging strategy: a clean, high-level summary for the user-facing console (Standard Output) and a verbose, detailed debug log (File Output) for developers and troubleshooting.

## 3. User Experience (UX) & Interaction
*   **Rich Visuals:** Utilize the `rich` library to deliver a polished CLI experience. Use color-coding for status updates, tables for result summaries, and dynamic progress bars to make the complex extraction process visually digestible.
*   **Interactive Safeguards:** For significant configuration actions (e.g., defining a new schema), the interface should verify user intent through confirmation prompts, reducing the risk of accidental misconfiguration.
*   **Silent/Batch Capability:** The tool must support a non-interactive mode (e.g., `--quiet`, `--json`) to enable seamless integration into larger automation scripts or CI/CD pipelines.
*   **GUI Foundation:** All core functionality must be exposed via a clean API layer (separating logic from the CLI presentation). This structural preparation is critical to support the future development of a Graphical User Interface (GUI) for non-technical users.

# Product Guide: SR-Architect

## 1. Vision
SR-Architect is an agentic ETL (Extract, Transform, Load) pipeline designed to revolutionize the systematic review process. By replacing manual data extraction with intelligent, audit-backed automation, it empowers researchers to synthesize evidence from dozens of papers in minutes rather than days. The ultimate goal is to uncover hidden insights through adaptive schema discovery and semantic analysis, making high-quality evidence synthesis accessible and scalable.

## 2. Target Audience
*   **Academic Researchers & Systematic Reviewers:** The primary users are researchers who need to synthesize data from large collections of PDF literature for publication and peer review. They value accuracy, speed, and the ability to verify findings against source text.

## 3. Core Goals
*   **Extreme Accuracy:** Eliminate hallucinations by ensuring every extracted data point is "self-proving"—backed by a verbatim quote from the source PDF for easy manual verification.
*   **High Throughput:** Dramatically reduce the time required for data extraction, processing 50+ papers efficiently to accelerate the research cycle.
*   **Reproducibility:** Maintain scientific rigor by logging every decision, prompt, and extraction step in a comprehensive audit trail, satisfying peer-review standards.

## 4. Key Features
*   **Self-Proving Extraction:** A robust extraction engine that pairs every structured value (e.g., patient count, dosage) with the exact text snippet from the document, enabling rapid validation.
*   **Interactive & Adaptive Schema Builder:** A flexible CLI tool that allows users to define custom variables *and* intelligently iterates over PDFs to discover and suggest relevant data points that the researcher may have missed.
*   **Semantic Querying & Insight Discovery:** A built-in vector store that allows users to "talk to their corpus," asking natural language questions to find specific evidence and visualizing data to reveal hidden patterns across the literature.

## 5. Success Metrics
*   **Extraction Confidence:** Achieving >95% accuracy on benchmark datasets (starting with Diffuse Pulmonary Meningotheliomatosis) and demonstrating consistent performance across diverse study designs (RCTs, observational studies, case reports).
*   **Auditability:** Producing detailed JSONL logs that capture the full reasoning chain, ensuring the extraction process is transparent and reproducible.
*   **Generalizability:** The platform must successfully scale beyond the initial DPM pilot to handle different systematic review topics and domains with minimal reconfiguration.
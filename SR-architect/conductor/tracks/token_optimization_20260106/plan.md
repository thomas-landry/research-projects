# Track Plan: Token Optimization & Hybrid Local/Cloud Architecture

## Phase 0: POC Validation & Baseline Metrics [checkpoint: 6f145c9]
- [x] Task: Select 15-20 representative PDFs (5 RCTs, 5 multi-column, 5 scanned) for the test set. 2049
- [x] Task: Create "golden dataset" of 20-30 manually verified extractions for these papers. 2151
- [x] Task: Establish baseline metrics from current Sonnet-only pipeline (cost/paper, tokens/field, accuracy/F1, latency).
- [x] Task: Document current pipeline performance in `BASELINE.md`.
- [x] Task: Conductor - User Manual Verification 'Phase 0: POC Validation & Baseline Metrics' (Protocol in workflow.md)

## Phase 1: Resource Management & Observability Foundation
- [ ] Task: Implement `ResourceManager` module to monitor M4 RAM (18GB ceiling, 14GB throttle trigger) and CPU usage (`psutil`).
- [ ] Task: Implement dynamic `max_workers` throttling in `BatchExecutor` based on system health.
- [ ] Task: Implement "Graceful Degradation" strategy: auto-escalate to cloud on local OOM.
- [ ] Task: Extend `TokenTracker` to log usage by (Tier × Field × Paper) and integrate `tiktoken`.
- [ ] Task: Implement "Circuit Breaker" pattern in `BatchExecutor`: bypass local model after N consecutive failures.
- [ ] Task: Add failure taxonomy logging to `AuditLogger` (OOM, timeout, schema_fail, low_confidence).
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Resource Management & Observability Foundation' (Protocol in workflow.md)

## Phase 2: Intelligent PDF Parsing & Pre-Processing
- [ ] Task: Create `ComplexityClassifier` with YAML config for PyMuPDF metrics (image >30%, text density).
- [ ] Task: Implement `TableExtractor` in `DocumentParser` using `pdfplumber`.
- [ ] Task: Implement parser fallback chain (Docling → PyMuPDF4LLM → Vision API).
- [ ] Task: Refactor `DocumentParser` to support "Smart Section Filtering" (strip References/Acknowledgments) via `ContentFilter`.
- [ ] Task: Implement `LayoutCleaner` in `ContentFilter` to fix hyphenation and column breaks.
- [ ] Task: Implement `PubMedFetcher` to retrieve structured abstracts via DOI.
- [ ] Task: Verify parsing robustness against the validation set (measure F1 vs baseline).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Intelligent PDF Parsing & Pre-Processing' (Protocol in workflow.md)

## Phase 3: Local LLM Integration & Advanced Chunking
- [ ] Task: Create `OllamaClient` with `OllamaHealthCheck` (auto-restart if unresponsive).
- [ ] Task: Create `ModelComparison` harness to benchmark Llama 3.1 8B vs Mistral/Qwen.
- [ ] Task: Implement `IMRADParser` (regex/heuristics) for section boundary detection.
- [ ] Task: Implement `FuzzyDeduplicator` (MinHash/RapidFuzz) to remove >90% similar blocks.
- [ ] Task: Implement `SemanticChunker` for non-standard formats (wrapping LangChain or custom).
- [ ] Task: Implement `ContextWindowMonitor` to prevent truncation.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Local LLM Integration & Advanced Chunking' (Protocol in workflow.md)

## Phase 4: Hybrid Cascading Extraction Pipeline
- [ ] Task: Create `FieldComplexityRouter` to assign fields to starting tiers (Tier 0/1/2).
- [ ] Task: Implement Tier 0 regex extraction for trivial fields (DOI, Year).
- [ ] Task: Create `ModelCascader` class to manage Tier 1 (Local) -> Tier 2 (Cheap Cloud) -> Tier 3 (Sonnet) logic.
- [ ] Task: Extend `ExtractionChecker` with `ConfidenceValidator` and configurable thresholds.
- [ ] Task: Implement `PromptCompressor` strategy: `LocalSummarizer` for pre-chunking, `LLMLingua` for Tier 2/3 calls.
- [ ] Task: Add "Self-Consistency" voting logic for critical numeric fields.
- [ ] Task: Implement `ManualReviewQueue` for papers where all tiers fail.
- [ ] Task: Connect `ExtractionChecker` to `ModelCascader` for schema validation at each tier.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Hybrid Cascading Extraction Pipeline' (Protocol in workflow.md)

## Phase 5: Granular Caching & Schema Evolution
- [ ] Task: Refactor `StateManager` to support field-level caching (Key: DocHash + FieldName + SchemaVersion).
- [ ] Task: Implement `SchemaVersionControl` to detect changes and trigger partial backfills.
- [ ] Task: Extend `AuditLogger` for tracking HITL reviews and manual overrides.
- [ ] Task: Implement `SchemaDiff` tool to preview backfill costs.
- [ ] Task: Add Pydantic validation for medical fields constraints.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Granular Caching & Schema Evolution' (Protocol in workflow.md)

## Phase 6: Integration Testing & Migration
- [ ] Task: Run smoke tests for each tier independently.
- [ ] Task: End-to-end regression test on 50-paper corpus (Pass: Cost -50%, Accuracy delta <2%).
- [ ] Task: Implement A/B validation on flagged subset.
- [ ] Task: Implement `--hybrid-mode` CLI flag and rollout/rollback procedure.
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Integration Testing & Migration' (Protocol in workflow.md)

## Phase 7: Documentation & Maintenance
- [ ] Task: Create `config/config.example.yaml` with all parameters.
- [ ] Task: Create troubleshooting guide and decision tree.
- [ ] Task: Write "adding new fields" playbook.
- [ ] Task: Update methods section template with hybrid pipeline details.
- [ ] Task: Conductor - User Manual Verification 'Phase 7: Documentation & Maintenance' (Protocol in workflow.md)

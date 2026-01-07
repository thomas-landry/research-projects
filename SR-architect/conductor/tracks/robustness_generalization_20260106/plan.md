# Track Plan: Robustness & Generalization — Adaptive Schema Discovery & Interactive Polish

## Phase 1: Foundation & Logging (Dual-Layer) [checkpoint: 72641cd]
- [x] Task: Implement verbose file logging alongside clean console output. 1984b66
- [x] Task: Create a base `DiscoveryAgent` interface. 336d4ea
- [x] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Logging' (Protocol in workflow.md) 72641cd

## Phase 2: Adaptive Schema Discovery [checkpoint: ccee37d]
- [x] Task: Implement the "Sampling" logic to select N papers for discovery. 826292e
- [x] Task: Develop the Discovery Agent prompt and extraction logic to find "novel variables". 892c06c
- [x] Task: Integrate discovery suggestions into the CLI interactive flow. bc311ad
- [x] Task: Refine discovery logic to run iteratively over the sample, accumulating new fields. f58b903
- [x] Task: Conductor - User Manual Verification 'Phase 2: Adaptive Schema Discovery' (Protocol in workflow.md) ccee37d

## Phase 3: Interactive Polish & Safety [checkpoint: ffe8dc8]
- [x] Task: Add "Undo" and "Delete Field" functionality to the interactive schema builder. 681dea8
- [x] Task: Implement confirmation prompts for large batch jobs and schema saves. 49f1b79
- [x] Task: Enhance CLI error reporting using `rich` panels for legibility. 2d74601
- [x] Task: Conductor - User Manual Verification 'Phase 3: Interactive Polish & Safety' (Protocol in workflow.md) ffe8dc8

## Phase 4: API Refactoring & Generalization
- [x] Task: Refactor extraction logic into a clean `ExtractionService` API. e68f2cb
- [ ] Task: Verify adaptive discovery on a secondary dataset (non-DPM).
- [ ] Task: Conductor - User Manual Verification 'Phase 4: API Refactoring & Generalization' (Protocol in workflow.md)

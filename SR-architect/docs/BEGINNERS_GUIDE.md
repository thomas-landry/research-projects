# SR-Architect: Beginner's Guide to Antigravity Orchestration

> **How to drive a systematic review extraction pipeline using Antigravity as your AI co-pilot**

This guide teaches you how to effectively orchestrate the SR-Architect pipeline using Antigravity, with copy-paste prompts and step-by-step workflows.

---

## Table of Contents

1. [What is Antigravity Orchestration?](#what-is-antigravity-orchestration)
2. [Setting Up the Orchestrating Agent](#setting-up-the-orchestrating-agent)
3. [The 5-Phase Extraction Workflow](#the-5-phase-extraction-workflow)
4. [Prompt Library: Copy-Paste Commands](#prompt-library)
5. [Calling Agents: When & How](#calling-agents)
6. [Continuous Orchestration: Keeping the Pipeline Running](#continuous-orchestration)
7. [Troubleshooting Common Issues](#troubleshooting)
8. [Advanced Orchestration Patterns](#advanced-patterns)

---

## What is Antigravity Orchestration?

**Antigravity** (me!) is an AI coding assistant that can:
- Run terminal commands
- Read/write files
- Analyze outputs
- Make decisions based on results

**Orchestration** means I coordinate multiple tools and agents to complete complex tasks—like conducting a systematic review extraction on 84 PDFs.

### The Mental Model

Think of it like this:

```
YOU (Researcher)
    ↓
    "Extract data from my DPM papers"
    ↓
ANTIGRAVITY (Orchestrator)
    ↓
    ├── Runs: python cli.py discover ./papers
    ├── Shows: suggested variables
    ├── Asks: "Approve this schema?"
    ├── Runs: python cli.py extract ./papers
    ├── Monitors: progress, errors
    ├── Reports: "82/84 complete, 2 need review"
    ↓
SR-ARCHITECT (Tool)
    ↓
OUTPUT: CSV + Vectors + Audit Log
```

---

## Setting Up the Orchestrating Agent

### Step 1: Ensure Your Environment is Ready

Before starting any extraction, tell me:

```
Check if SR-Architect is ready to run. Install any missing dependencies.
```

I will:
1. Check Python version
2. Verify dependencies are installed
3. Check for `.env` with API keys
4. Report any issues

### Step 2: Set Your Working Context

At the start of each session, establish context:

```
I'm working on a systematic review of [TOPIC].
My screened PDFs are in: [PATH]
I want to extract [VARIABLES] from each paper.
```

**Example:**
```
I'm working on a systematic review of Diffuse Pulmonary Meningotheliomatosis.
My screened PDFs are in: ~/Projects/research-projects/DPM-systematic-review/papers
I want to extract patient demographics, imaging findings, histopathology, and outcomes.
```

### Step 3: Confirm API Key Configuration

```
Verify my OpenRouter API key is configured for SR-Architect.
```

I'll check `.env` and confirm the key is set.

---

## The 5-Phase Extraction Workflow

### Phase 1: Discovery 🔍

**Goal**: Analyze sample papers to discover what data can be extracted.

**Prompt to use:**
```
Run schema discovery on 3 papers from my DPM folder. 
Show me what variables the tool suggests.
```

**What I'll do:**
```bash
python cli.py discover ../DPM-systematic-review/papers --sample 3
```

**Expected output:**
- Table of discovered variables
- Frequency (how many papers had each variable)
- Example values
- JSON file with full schema

**Follow-up prompts:**
- "Add 'smoking_status' to the schema"
- "Remove 'funding_source', it's not relevant"
- "Show me the case_report predefined schema instead"

---

### Phase 2: Schema Approval ✅

**Goal**: Finalize the extraction schema before full run.

**Prompt to use:**
```
Show me the extraction schema we'll use. 
List all fields with their types and whether they're required.
I want to add [X] and remove [Y].
```

**Or for predefined:**
```
Use the case_report schema. Show me what fields it includes.
```

**What I'll do:**
```bash
python cli.py schemas  # Show available schemas
```

Then present the schema for your approval.

---

### Phase 3: Test Extraction 🧪

**Goal**: Run on 3-5 papers to verify extraction quality.

**Prompt to use:**
```
Run a test extraction on 5 papers using the case_report schema.
Show me the results and any errors.
```

**What I'll do:**
```bash
python cli.py extract ../DPM-systematic-review/papers \
    --schema case_report \
    --limit 5 \
    --output output/test_results.csv \
    --verbose
```

**Follow-up prompts:**
- "Show me the CSV output"
- "Why did paper X fail?"
- "The ages look wrong, can we re-extract with a better prompt?"

---

### Phase 4: Full Extraction 🚀

**Goal**: Extract from all papers with monitoring.

**Prompt to use:**
```
Run the full extraction on all 84 DPM papers.
Use checkpointing so we can resume if it stops.
Flag any low-confidence extractions for my review.
```

**What I'll do:**
```bash
python cli.py extract ../DPM-systematic-review/papers \
    --schema case_report \
    --output output/dpm_full_results.csv \
    --resume
```

Then monitor progress and report:
- Papers completed
- Papers failed
- Estimated time remaining
- Any issues

---

### Phase 5: Review & Refinement 🔎

**Goal**: Validate results and handle edge cases.

**Prompts to use:**
```
Show me a summary of the extraction results.
How many papers had missing patient_age?
Which papers were flagged for human review?
```

```
For the 2 papers that failed, try to extract them manually 
and explain what went wrong.
```

```
Generate the methods text for my manuscript.
```

---

## Prompt Library

### Setup & Configuration

| What you want | Prompt |
|---------------|--------|
| Check setup | "Is SR-Architect ready to run? Check dependencies and API keys." |
| Set API key | "Add my OpenRouter API key to SR-Architect: sk-or-v1-xxx" |
| List schemas | "Show me all available extraction schemas" |
| Check papers | "How many PDFs are in my DPM papers folder?" |

### Discovery & Schema

| What you want | Prompt |
|---------------|--------|
| Discover variables | "Run schema discovery on 3 papers and show me suggestions" |
| Use predefined | "Use the case_report schema for my extraction" |
| Custom schema | "I want to extract: patient_age, patient_sex, symptoms, imaging, treatment, outcome" |
| Modify schema | "Add 'smoking_status' as an optional text field" |

### Extraction

| What you want | Prompt |
|---------------|--------|
| Test run | "Extract from 5 papers as a test, show verbose output" |
| Full run | "Run full extraction on all papers with checkpointing" |
| Resume | "Resume the extraction that was interrupted" |
| Faster model | "Use gpt-4o-mini instead for cost savings" |
| Skip vectors | "Run extraction without storing vectors" |

### Review & Analysis

| What you want | Prompt |
|---------------|--------|
| View results | "Show me the first 10 rows of the extraction CSV" |
| Check failures | "Which papers failed and why?" |
| Find patterns | "How many papers reported immunohistochemistry results?" |
| Missing data | "Which papers have missing patient_age values?" |
| Query corpus | "Search the vector store for papers mentioning 'ground-glass opacities'" |

### Output & Documentation

| What you want | Prompt |
|---------------|--------|
| Methods text | "Generate the methods section for my manuscript" |
| Export log | "Show me the audit log for this extraction session" |
| Stats summary | "Give me statistics on the extraction: success rate, time, etc." |

---

## Calling Agents: When & How

### Agent: Schema Discovery

**When to call**: At the START of a new review, before defining your schema.

**How to call**:
```
Discover what variables I can extract from my papers.
```

**What it does**:
- Reads 3 sample papers
- Asks LLM: "What data points exist here?"
- Aggregates suggestions
- Presents for your approval

---

### Agent: Extractor

**When to call**: After schema is approved.

**How to call**:
```
Extract data from all papers using the approved schema.
```

**What it does**:
- Parses each PDF
- Sends context to LLM with Pydantic schema
- Validates response
- Writes to CSV

---

### Agent: Confidence Router

**When to call**: Automatically called after each extraction.

**How it works**:
- Scores extraction quality (0-1)
- Routes to: auto_approve, human_review, or re_extract
- Flags uncertain extractions

**How to query**:
```
Which papers were flagged as low confidence?
```

---

### Agent: Auditor (Future)

**When to call**: After extraction, before finalizing.

**How to call**:
```
Verify the extraction quality for papers flagged for review.
```

**What it will do**:
- Compare extracted values with source quotes
- Check for contradictions
- Assign confidence scores

---

## Continuous Orchestration

### The Key to Non-Stop Workflow

To keep the pipeline running without interruption, use **chained prompts** that include next steps:

**Pattern 1: Conditional Continuation**
```
Run the extraction. When complete:
- If success rate > 95%, proceed to generate methods text
- If any failures, show me the failed papers and pause
```

**Pattern 2: Batch Processing**
```
Process papers in batches of 20. After each batch:
- Save checkpoint
- Report progress
- Continue unless I interrupt
```

**Pattern 3: Error Recovery**
```
If extraction fails for a paper:
- Log the error
- Try with PyMuPDF parser instead
- If still fails, skip and continue
- Show all skipped papers at the end
```

### Example: Full Automated Run

```
I'm ready to extract my DPM systematic review.

1. First, run discovery on 3 papers and show me the schema
2. After I approve, run test extraction on 5 papers
3. Show me test results with any issues
4. If test looks good, run full extraction on all papers
5. Use checkpointing and resume if interrupted
6. When complete, generate methods text and show extraction stats
7. Flag any papers that need my manual review

Start with step 1.
```

I will execute each step, show you results, and wait for "continue" or "proceed" before moving to the next step that requires approval.

---

## Troubleshooting

### "Docling not installed"

**Prompt:**
```
Install Docling for PDF parsing. If it fails, set up PyMuPDF as fallback.
```

### "OPENROUTER_API_KEY not set"

**Prompt:**
```
My OpenRouter key is sk-or-v1-xxx. Add it to SR-Architect's .env file.
```

### "Extraction failed for paper X"

**Prompt:**
```
Why did extraction fail for [paper.pdf]? Show me the error and try again.
```

### "Results look wrong"

**Prompt:**
```
The patient ages are all "Not reported" but I know they're in the papers.
Can we adjust the extraction prompt or look at a specific paper?
```

### "Need to resume after crash"

**Prompt:**
```
Resume the extraction that was running. 
Show me what was already completed.
```

---

## Advanced Patterns

### Pattern: Incremental Schema Refinement

```
1. Extract 10 papers with current schema
2. Review results
3. I notice many papers have "comorbidities" - add that field
4. Re-extract only the 10 papers with new schema
5. Continue with remaining papers
```

### Pattern: Multi-Model Strategy

```
For expensive fields (histopathology, complex outcomes):
- Use claude-sonnet-4 for high accuracy

For simple fields (age, sex):
- Use gpt-4o-mini for speed

Extract in two passes and merge results.
```

### Pattern: Validation Loop

```
1. Extract all papers
2. Run confidence scoring
3. For papers with score < 0.7:
   - Show me the extraction
   - I'll manually correct
4. Merge manual corrections into final CSV
```

### Pattern: Parallel Extraction

```
Run extraction with 4 parallel workers to speed up processing.
Estimate time savings compared to sequential.
```

---

## Quick Reference Card

### Starting a Session
```
I'm working on [TOPIC] SR. Papers are in [PATH].
Check if SR-Architect is ready, then run discovery on 3 papers.
```

### Running Extraction
```
Use [SCHEMA] schema. Test on 5 papers first, then full run.
Enable checkpointing. Flag low-confidence for review.
```

### Reviewing Results
```
Show extraction summary: success rate, failures, missing data.
Generate methods text for my manuscript.
```

### Handling Issues
```
Why did [X] fail? Try again with [APPROACH].
Resume the interrupted extraction.
```

---

## Summary: The 3 Golden Prompts

If you remember nothing else, these 3 prompts will get you through most extractions:

### 1. Setup
```
I have 84 PDFs in ~/Projects/research-projects/DPM-systematic-review/papers.
Run schema discovery on 3 papers and recommend extraction variables.
```

### 2. Extract
```
Use the case_report schema. Test on 5 papers, then if OK, 
run full extraction with checkpointing.
```

### 3. Review
```
Show me the results summary. Flag any issues.
Generate methods text for my manuscript.
```

---

*Happy extracting! 🔬*

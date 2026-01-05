# SR-Architect + Antigravity: Agent Orchestration Guide

This guide explains how to use Antigravity (your AI coding assistant) as an orchestrator for the SR-Architect systematic review pipeline.

---

## The Orchestration Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         ANTIGRAVITY                              │
│                    (Agent Orchestrator)                          │
│                                                                  │
│   "Extract data from my DPM papers using case_report schema"    │
│                              │                                   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. Understand intent                                     │   │
│   │ 2. Select appropriate SR-Architect command               │   │
│   │ 3. Execute CLI with correct parameters                   │   │
│   │ 4. Monitor progress and handle errors                    │   │
│   │ 5. Interpret results and present to user                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                      SR-ARCHITECT CLI                            │
│                  (Tool being orchestrated)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step: Using Antigravity for Extraction

### Step 1: Preparation

Before starting, ensure your environment is ready:

```
You: "Check if SR-Architect dependencies are installed"

Antigravity will:
1. Run `pip list | grep -E 'docling|instructor|chromadb'`
2. Report missing packages
3. Offer to install: `pip install -r requirements.txt`
```

### Step 2: Define Your Schema

Tell Antigravity what data you need:

```
You: "I need to extract: patient age, sex, presenting symptoms, 
      imaging findings, histopathology, and outcome from my DPM papers"

Antigravity will:
1. Recognize this matches the predefined `case_report` schema
2. Or offer to build a custom schema interactively
3. Show you the fields that will be extracted
```

### Step 3: Run Extraction

Request the extraction:

```
You: "Extract data from the 84 papers in DPM-systematic-review/papers"

Antigravity will:
1. Run: `python cli.py extract ../DPM-systematic-review/papers 
         --schema case_report --output output/dpm_results.csv`
2. Monitor progress
3. Report: "Extracted 82/84 papers. 2 failed (see audit log)"
```

### Step 4: Validate Results

Ask Antigravity to check the output:

```
You: "Show me the first 5 rows of the extraction"

Antigravity will:
1. Read `output/dpm_results.csv`
2. Display a formatted table
3. Highlight any missing values
```

### Step 5: Query Your Corpus

Use semantic search:

```
You: "Find papers that discuss ground-glass opacities in imaging"

Antigravity will:
1. Run: `python cli.py query "ground-glass opacities imaging"`
2. Return matching text chunks with source files
3. Offer to show full context
```

### Step 6: Generate Documentation

For your manuscript:

```
You: "Generate the methods text for my extraction"

Antigravity will:
1. Run: `python cli.py methods`
2. Present the auto-generated reproducibility text
3. Offer to refine or expand it
```

---

## Natural Language Commands → CLI Mapping

| You Say | Antigravity Executes |
|---------|---------------------|
| "Extract data from papers in X folder" | `python cli.py extract X --schema case_report` |
| "Use the RCT schema for this review" | `python cli.py extract X --schema rct` |
| "Let me define my own variables" | `python cli.py extract X --interactive` |
| "Just test on 5 papers first" | `python cli.py extract X --limit 5` |
| "Search for papers about [topic]" | `python cli.py query "[topic]"` |
| "How many papers did we process?" | `python cli.py stats` |
| "Generate methods section" | `python cli.py methods` |
| "Show me the extraction log" | `cat output/logs/extraction_*.jsonl` |

---

## Advanced Orchestration Patterns

### Pattern 1: Iterative Refinement

```
You: "Extract the papers, then show me any with missing patient age"

Antigravity will:
1. Run extraction
2. Load CSV and filter rows where patient_age is "Not reported" or empty
3. Show the filenames
4. Offer: "Want me to re-extract these with a more aggressive prompt?"
```

### Pattern 2: Cross-Reference

```
You: "Compare the extracted treatments across all 84 papers"

Antigravity will:
1. Load the CSV
2. Analyze the `treatment` column
3. Group and count unique treatments
4. Present a summary table
```

### Pattern 3: Error Recovery

```
You: "2 papers failed extraction. Why?"

Antigravity will:
1. Parse the audit log JSONL
2. Find entries with `"status": "error"`
3. Show error messages
4. Suggest fixes (OCR, different section targeting)
```

### Pattern 4: Multi-Step Synthesis

```
You: "Extract, then summarize the key findings by patient demographics"

Antigravity will:
1. Run extraction
2. Load CSV
3. Group by age ranges and sex
4. Generate narrative summary
5. Identify patterns across subgroups
```

---

## Available Skills Integration

SR-Architect works with your existing LandryAssistant skills:

| Skill | Integration Point |
|-------|-------------------|
| `literature-review` | Find papers to screen → SR-Architect extracts |
| `citation-management` | Extract DOIs → validate with citation-management |
| `scientific-writing` | Extraction → CSV → manuscript drafting |
| `exploratory-data-analysis` | CSV output → statistical analysis |
| `matplotlib/seaborn` | CSV data → publication figures |
| `pymc` | Extracted effect sizes → Bayesian meta-analysis |

---

## Troubleshooting via Antigravity

| Problem | What to Tell Antigravity |
|---------|-------------------------|
| No API key | "Set up my OpenRouter API key for SR-Architect" |
| Docling errors | "Install Docling and its dependencies" |
| Empty extractions | "Why is the CSV empty for paper X?" |
| Slow performance | "Can we use a faster model for extraction?" |
| Need OCR | "Enable OCR for scanned PDFs" |

---

## Best Practices

1. **Start Small**: Always test with `--limit 3` before full extraction
2. **Check Quotes**: Verify `_quote` fields match your source PDFs
3. **Use Predefined Schemas**: They're optimized for common study types
4. **Save Your Schema**: If using interactive mode, save the field definitions
5. **Review Audit Logs**: They're your reproducibility documentation

---

## Example Full Workflow

```
Session with Antigravity:

You: Let's start the DPM systematic review extraction.

Antigravity: I see you have 84 PDFs in DPM-systematic-review/papers. 
The case_report schema is appropriate for this study type. 
Should I proceed with extraction?

You: Yes, but test on 5 papers first.

Antigravity: Running extraction on 5 papers...
[Progress bar]
Done! 5/5 successful. Here's a preview:
| filename | patient_age | patient_sex | presenting_symptoms |
|----------|-------------|-------------|---------------------|
| Smith.pdf | 52 | Female | Progressive dyspnea |
...

You: Looks good. Run the full extraction.

Antigravity: Processing 84 papers...
[Progress bar]
Complete! 82/84 successful, 2 failed.
CSV saved to: output/dpm_results.csv
Want me to show the failed papers?

You: Yes, and then generate the methods text.

Antigravity: Failed papers:
1. Zhang_2023.pdf - Scanned PDF, OCR needed
2. corrupted_file.pdf - Invalid PDF format

Methods text generated:
"Data extraction was performed using SR-Architect...
82 papers successfully extracted with 97.6% success rate..."
```

---

*SR-Architect + Antigravity: Your AI-powered systematic review workflow.*

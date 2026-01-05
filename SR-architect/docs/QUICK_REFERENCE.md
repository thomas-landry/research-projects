# SR-Architect Quick Reference Card

## 🚀 The 3 Golden Prompts

### 1. Setup
```
I have [N] PDFs in [PATH].
Run schema discovery on 3 papers and recommend extraction variables.
```

### 2. Extract
```
Use the [SCHEMA] schema. Test on 5 papers, then if OK,
run full extraction with checkpointing.
```

### 3. Review
```
Show me the results summary. Flag any issues.
Generate methods text for my manuscript.
```

---

## 📋 Available Schemas

| Schema | Use Case |
|--------|----------|
| `case_report` | Case reports/series |
| `rct` | Randomized trials |
| `observational` | Cohort, case-control |
| `interactive` | Build your own |

---

## 🛠️ CLI Commands

```bash
# Discover variables
python cli.py discover ./papers --sample 3

# Run extraction
python cli.py extract ./papers --schema case_report -o results.csv

# With options
python cli.py extract ./papers \
    --schema case_report \
    --limit 10 \
    --resume \
    --verbose

# Query vectors
python cli.py query "treatment outcomes"

# Generate methods
python cli.py methods
```

---

## 🎯 Phase Workflow

```
DISCOVER → APPROVE → TEST → EXTRACT → REVIEW
   3 papers   User    5 papers  All    Verify
```

---

## 🤖 Agents

| Agent | Purpose | When to Call |
|-------|---------|--------------|
| Discovery | Find variables | Start of new review |
| Extractor | Pull structured data | After schema approval |
| Confidence | Score quality | Auto after extraction |
| Auditor | Verify accuracy | For flagged papers |

---

## ⚠️ Common Issues

| Problem | Prompt |
|---------|--------|
| Missing API key | "Add my OpenRouter key: sk-or-v1-xxx" |
| Paper failed | "Why did [paper] fail? Try again" |
| Need to resume | "Resume the interrupted extraction" |
| Wrong data | "Re-extract [paper] with focus on [field]" |

---

## 📊 Output Files

```
output/
├── results.csv           # Extracted data
├── vector_store/         # ChromaDB
├── pipeline_state.json   # For resume
└── logs/
    ├── extraction_*.jsonl
    └── summary_*.json
```

---

## 🔗 Continuous Orchestration

Keep pipeline running with:

```
Run extraction. After each batch:
- Save checkpoint
- Report progress  
- Continue unless I interrupt
```

---

*Full guide: docs/BEGINNERS_GUIDE.md*

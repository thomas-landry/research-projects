# SR-Architect: Systematic Review Data Extraction Pipeline

> **Agentic ETL for Evidence Synthesis** — Transform 50+ screened PDFs into analysis-ready structured data with near-100% accuracy and full audit trails.

---

## 🎯 What This Tool Does

SR-Architect automates the most time-consuming part of systematic reviews: **data extraction**. Instead of manually reading each paper and copying values into a spreadsheet, you:

1. **Point it at your screened PDFs**
2. **Define what variables to extract** (or use predefined schemas)
3. **Get a clean CSV** with extracted data + source quotes for verification
4. **Query your corpus semantically** ("find papers discussing treatment outcomes")

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SR-ARCHITECT PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │ INPUTS   │───▶│  PARSER  │───▶│ EXTRACTOR│───▶│   CSV    │         │
│   │(PDF/HTML)│    │(Docling+)│    │(Instructor)   │ (output) │         │
│   └──────────┘    └────┬─────┘    └────┬─────┘    └──────────┘         │
│                        │               │                                 │
│                        ▼               ▼                                 │
│                  ┌──────────┐    ┌──────────┐                           │
│                  │  CHUNKS  │───▶│ CHROMADB │◀── Semantic Query         │
│                  │ (semantic)│    │ (vectors)│                           │
│                  └──────────┘    └──────────┘                           │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────┐      │
│   │                      AUDIT LOGGER                             │      │
│   │   Every extraction logged → JSONL → Methods section text     │      │
│   └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Excellence-Focused Pipeline (v3)

The pipeline has evolved to prioritize **provenance** and **precision** over simple extraction:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       EXCELLENCE-FOCUSED CASCADE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐     ┌───────────┐    │
│  │ Semantic   │───▶│ Content    │───▶│ Relevance  │────▶│ Extractor │    │
│  │ Chunker    │    │ Filter     │    │ Classifier │     │ (Hybrid)  │    │
│  │ (LLM-Split)│    │ (Exclude)  │    │ (Include)  │     │           │    │
│  └────────────┘    └────────────┘    └─────┬──────┘     └─────┬─────┘    │
│         ▲                                  │                  │          │
│         │                                  ▼              ┌───▼──┐       │
│  ┌────────────┐                      ┌────────────┐       │ Sent │       │
│  │  Parser    │                      │ Recall     │◀─────▶│ Ext. │       │
│  │ (Docling)  │                      │ Booster    │       └──────┘       │
│  └────────────┘                      └────────────┘                      │
│                                            ▲                             │
│                                            │ (Feedback Loop)             │
│   ┌────────────────────────────────────────┴───────────────────────┐     │
│   │  Validation: Fuzzy Matching, Cross-checking, Range Validation  │     │
│   │  Provenance: Character-level offsets (EvidenceFrames)          │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**New Capabilities (v3):**
- **Semantic Chunking (Phase D)**: Uses LLMs to identify logical sections (Methods, Results) instead of brittle headers.
- **Unit-Context Extraction (Phase B)**: "Needle-in-a-haystack" extraction for complex fields using concurrently processed sentence windows.
- **Precise Provenance (Phase E)**: Tracks exact character start/end indices for every extracted fact ("Click-to-Source").
- **Recall Boost (Phase C)**: Automatically expands search scope if critical fields come back empty.
- **Fuzzy Validation (Phase A)**: Ensures every "exact quote" actually exists in the text, preventing hallucination.

**Key benefits:**
- **50%+ cost reduction** via local-first extraction
- **Self-consistency voting** for critical numeric fields
- **Caching** to avoid re-processing unchanged documents
- **Auto-correction** for common OCR and extraction errors

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ~/Projects/research-projects/SR-architect
pip install -r requirements.txt
```

**Core dependencies:**
- `docling` — IBM's academic PDF parser (handles multi-column, tables)
- `instructor` — Structured LLM outputs via Pydantic
- `chromadb` — Vector database for semantic search
- `typer` + `rich` — Beautiful CLI interface

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env:
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Run Your First Extraction

```bash
# Test on 3 papers first
python cli.py extract ../DPM-systematic-review/papers \
    --schema case_report \
    --limit 3 \
    --output output/test_results.csv \
    --verbose

# Full extraction (84 DPM papers)
python cli.py extract ../DPM-systematic-review/papers \
    --schema case_report \
    --output output/dpm_extraction.csv
```

---

## 📋 Available Commands

### `extract` — Main Extraction Pipeline

```bash
python cli.py extract <papers_dir> [OPTIONS]

Options:
  -o, --output PATH      Output CSV path [default: ./output/extraction_results.csv]
  -s, --schema TEXT      Schema: case_report, rct, observational, interactive
  -i, --interactive      Build custom schema interactively
  -l, --limit INT        Process only N papers (for testing)
  -p, --provider TEXT    LLM: openrouter or ollama [default: openrouter]
  -m, --model TEXT       Override model selection
  --no-vectorize         Skip ChromaDB storage
  -v, --verbose          Show detailed progress
  --hierarchical         Enable hierarchical extraction (requires --theme)
  --theme TEXT           Theme for relevance filtering (required for hierarchical)
  --resume               Resume from last checkpoint
  --adaptive             Automatically discover schema from first 3 papers
  --hybrid-mode/--no-hybrid-mode  Use hybrid local-first extraction [default: enabled]
```

**Examples:**
```bash
# Use predefined case report schema
python cli.py extract ./papers --schema case_report

# Interactive schema builder
python cli.py extract ./papers --interactive

# Use local Ollama instead of OpenRouter
python cli.py extract ./papers --provider ollama --model llama3.1:8b

# Hierarchical extraction for specific theme
python cli.py extract ./papers --hierarchical --theme "adverse events"
```

### `discover` — Adaptive Schema Discovery

Analyze sample papers to automatically generate an extraction schema:

```bash
python cli.py discover <papers_dir> [OPTIONS]

Options:
  -n, --sample INT       Number of papers to analyze [default: 3]
  -o, --output PATH      Save schema to JSON [default: ./discovered_schema.json]
```

### `benchmark` — Model Performance Testing

Run partial extraction benchmarks across multiple local models:

```bash
python cli.py benchmark <papers_dir> --models "llama3.1:8b,mistral:7b"
```

### `query` — Semantic Search

Search your extracted corpus using natural language:

```bash
python cli.py query "treatment outcomes in elderly patients" --limit 5
python cli.py query "ground-glass opacities" --filename "Smith_2023.pdf"
```

### `schemas` — List Predefined Schemas

```bash
python cli.py schemas
```

**Available schemas:**
| Schema | Use Case | Key Fields |
|--------|----------|------------|
| `case_report` | Case reports/series | patient_age, presenting_symptoms, diagnosis, outcome |
| `rct` | Randomized trials | sample_size, intervention, comparator, primary_outcome |
| `observational` | Cohort/case-control | exposure, outcome, effect_estimate, confounders |

### `stats` — Vector Store Statistics

```bash
python cli.py stats
```

### `methods` — Generate Methods Text

Auto-generate reproducibility text for your methods section:

```bash
python cli.py methods
```

---

## 🔬 Schema Deep Dive

### Predefined: Case Report Schema (DPM)

Perfect for case reports and case series. Extracts:

| Field | Type | Description |
|-------|------|-------------|
| `case_count` | Integer | Number of cases in the report |
| `patient_age` | Text | Patient age(s) |
| `patient_sex` | Text | Male/Female/Other |
| `presenting_symptoms` | Text | Initial symptoms |
| `diagnostic_method` | Text | How diagnosis was made |
| `imaging_findings` | Text | CT/X-ray findings |
| `histopathology` | Text | Pathology results |
| `immunohistochemistry` | Text | IHC markers (optional) |
| `treatment` | Text | Treatment provided (optional) |
| `outcome` | Text | Patient outcome |
| `comorbidities` | Text | Associated conditions (optional) |

**Each field also extracts a `_quote` with the exact source text for verification.**

### Building Custom Schemas

```bash
python cli.py extract ./papers --interactive
```

The interactive builder will:
1. Ask for field names
2. Ask for descriptions (guides the LLM)
3. Set data types (text, integer, float, boolean, list)
4. Configure required vs optional
5. Enable/disable source quote capture

---

## 🤖 Multi-Agent Architecture

The pipeline is built on a specialized agentic architecture:

### Agent 1: Screener (`ScreeningDecision`)
- **Status**: Implemented (`agents/screener.py`)
- **Input**: Abstracts
- **Task**: Intelligent inclusion/exclusion based on PICO criteria

### Agent 2: Extractor (`StructuredExtractor`)
- **Status**: Core Implementation (`core/extractor.py`)
- **Task**: Extracts structured data with self-proving quotes

### Agent 3: Auditor (`ExtractionChecker`)
- **Status**: Implemented (`core/extraction_checker.py`)
- **Task**: Validates extractions against source text and logic rules

### Agent 4: Synthesizer (`SynthesizerAgent`)
- **Status**: Implemented (`agents/synthesizer.py`)
- **Task**: Aggregates extracted data into meta-analysis reports
- **Output**: Markdown narrative + statistical summaries

### Pipeline: `HierarchicalExtractionPipeline`
- Orchestrates the entire flow: Parsing -> Screening -> Extraction -> Validation -> Retry Loop

## 📊 Output Files

After extraction, you'll find:

```
output/
├── extraction_results.csv      # Main structured data
├── vector_store/               # ChromaDB files (portable)
│   └── chroma.sqlite3
└── logs/
    ├── extraction_20260104_191000.jsonl   # Full audit log
    └── summary_20260104_191000.json       # Session summary
```

### CSV Output

The CSV contains:
- All schema fields with extracted values
- `*_quote` columns with source text evidence
- `filename` column for paper identification
- `extraction_confidence` and `extraction_notes`

### Audit Log (JSONL)

Each line is a JSON object:
```json
{
  "timestamp": "2026-01-04T19:10:00Z",
  "filename": "Smith_2023.pdf",
  "status": "success",
  "chunks_created": 42,
  "vectors_stored": 42,
  "extraction_model": "claude-sonnet-4-20250514",
  "fields_extracted": {"patient_age": "52", "patient_sex": "Female", ...},
  "duration_seconds": 3.2
}
```

---

## ⚡ Optimization Tips

### 1. Batch Processing

For large reviews (100+ papers), process in batches:
```bash
python cli.py extract ./papers --limit 25 --output batch1.csv
python cli.py extract ./papers --limit 25 --output batch2.csv  # TODO: offset flag
```

### 2. Model Selection

| Model | Speed | Accuracy | Cost |
|-------|-------|----------|------|
| `claude-sonnet-4-20250514` | Medium | Highest | $$$ |
| `gpt-4o` | Fast | High | $$ |
| `gpt-4o-mini` | Fastest | Good | $ |
| `llama3.1:8b` (Ollama) | Varies | Moderate | Free |

### 3. Context Window Optimization

The pipeline automatically:
- Prioritizes Abstract + Methods + Results sections
- Truncates to 15,000 characters
- Ignores References and Acknowledgments

### 4. Error Recovery

Failed extractions are logged but don't stop the pipeline. Review the audit log:
```bash
grep '"status": "error"' output/logs/*.jsonl
```

---

## 🔗 Integration with Antigravity

SR-Architect is designed to work with your existing LandryAssistant ecosystem:

### Workflow 1: Literature Review → Extraction

1. Use `perplexity-search` to find relevant papers
2. Screen papers manually (or use future Screener agent)
3. Run SR-Architect extraction
4. Analyze CSV with `exploratory-data-analysis`

### Workflow 2: Extraction → Manuscript

1. Run extraction on screened papers
2. Use `methods` command for reproducibility text
3. Query vector store for specific findings
4. Use `scientific-writing` skill for manuscript drafting

---

## 🛠️ Troubleshooting

### "Docling not installed"
```bash
pip install docling
# Note: Requires Python 3.10+
```

### "OPENROUTER_API_KEY not set"
```bash
cp .env.example .env
# Add your key to .env
```

### "Insufficient text extracted"
Some PDFs may be scanned images. Enable OCR:
```python
# In parser.py, set use_ocr=True
parser = DocumentParser(use_ocr=True)
```

### Empty/missing fields in CSV
- Check the audit log for errors
- Verify the schema matches your paper type
- Some papers genuinely don't report certain data → "Not reported"

---

## 📚 References

- [Docling Documentation](https://github.com/docling-project/docling)
- [Instructor Library](https://python.useinstructor.com/)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [OpenRouter API](https://openrouter.ai/docs)

---

## License

Personal research use for Dr. Thomas Landry.

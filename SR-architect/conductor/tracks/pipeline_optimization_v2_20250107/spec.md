# Track Spec: Pipeline Optimization v2 (Streamlined)

## 1. Overview

This track represents a **streamlined redesign** of the original Token Optimization track, informed by a comprehensive pipeline evaluation. The goal remains the same—drastically reduce API costs while maintaining accuracy—but the implementation is simplified to eliminate over-engineering and focus on high-ROI optimizations.

**Key Changes from Original Track:**
- Reduced from 8 phases to 5 phases (~40% fewer tasks)
- Eliminated low-ROI components (LayoutCleaner, SchemaVersionControl, LLMLingua)
- Added high-impact missing features (PubMed metadata fetch, abstract-first extraction)
- Simplified model selection (Qwen 2.5 7B as primary local model)
- Streamlined caching strategy

## 2. Core Architecture

### 2.1 Extraction Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRE-EXTRACTION                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  PDF Input                                                              │
│      │                                                                  │
│      ├──► DOI Extraction (Regex) ──► PubMed/CrossRef Fetch             │
│      │                                    │                             │
│      │                                    ▼                             │
│      │                           Structured Abstract?                   │
│      │                              YES │ NO                            │
│      │                                  │  │                            │
│      │              ┌───────────────────┘  └──────────────┐             │
│      │              ▼                                     ▼             │
│      │    Abstract-First Extraction              Full PDF Parse        │
│      │              │                             (Docling)            │
│      │              ▼                                     │             │
│      │    40-60% fields extracted                        │             │
│      │              │                                     │             │
│      └──────────────┴─────────────────────────────────────┘             │
│                                    │                                    │
│                                    ▼                                    │
│                          Section Filtering                              │
│                   (Strip References, Acknowledgments)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTRACTION CASCADE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │   TIER 0    │   │   TIER 1    │   │   TIER 2    │   │   TIER 3    │ │
│  │   Regex     │   │   Local     │   │ Cloud-Lite  │   │Cloud-Premium│ │
│  │             │   │ Qwen3-14B   │   │ Gemini Flash│   │   Sonnet    │ │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘ │
│         │                 │                 │                 │         │
│         ▼                 ▼                 ▼                 ▼         │
│     DOI, Year         Demographics      General Ext.      Histopath     │
│     Journal           Study Type        CSV Template      Figures       │
│     Sample Size*      Primary Outcome   100+ Fields*      Complex       │
│     Age (formatted)   Criteria          (Chunked)         Eligibility   │
│                                                                         │
│  * With validation    Conf > 0.85 ──► ACCEPT                           │
│                       Conf < 0.85 ──► Escalate to next tier            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         POST-EXTRACTION                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Validation Rules ──► Auto-Correction ──► Cache Write ──► Output       │
│  (Range, Cross-field)  (OCR fixes)        (SQLite)        (JSONL)      │
│                                                                         │
│  If all tiers fail ──► Manual Review Queue                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model Strategy (Updated January 2025)

> **Note:** Updated based on comprehensive model evaluation. See `model_evaluation.md` for full analysis.

| Component | Model | Backend | Tier | Rationale |
|-----------|-------|---------|------|-----------|
| **Primary Local** | **Qwen3-14B** | Ollama | 1 | Qwen3-14B ≈ Qwen2.5-32B; best for privacy-first extraction |
| **Cloud Lite** | **Gemini 2.0 Flash Lite** | OpenRouter | 2 | **BEST VALUE**: $0.07/M tokens; handles massive schemas via chunking |
| **Cloud Cheap** | gpt-4o-mini | OpenAI | 2 | Solid fallback for general tasks |
| **Cloud Premium** | claude-3.5-sonnet | Anthropic | 3 | Complex interpretation only |

**Why Qwen3 over Qwen2.5:**
- ~2x parameter efficiency (Qwen3-14B ≈ Qwen2.5-32B)
- 36T training tokens (vs 18T for Qwen2.5)
- Native hybrid thinking/non-thinking modes
- Significantly better instruction following and structured output adherence

### 2.3 Field Routing Configuration

```yaml
# config/field_routing.yaml
field_routing:
  tier_0_regex:
    fields: [doi, publication_year, journal_name]
    patterns:
      doi: '10\.\d{4,}/[^\s]+'
      publication_year: '(19|20)\d{2}'
    
  tier_0_regex_with_validation:
    fields: [sample_size_raw, age_mean_sd, sex_ratio]
    requires_context_check: true
    
  tier_1_lightweight:
    model: "llama3.2:3b-instruct-q4_K_M"
    fields: [study_type_simple, single_center_bool, prospective_bool, country]
    confidence_threshold: 0.90
    max_context_tokens: 2048
    
  tier_1_standard:
    model: "qwen2.5:7b-instruct-q4_K_M"
    fields:
      - inclusion_criteria
      - exclusion_criteria
      - primary_outcome
      - intervention_description
      - follow_up_duration
      - study_design_detailed
    confidence_threshold: 0.85
    max_context_tokens: 4096
    
  tier_2_cloud:
    model: "gpt-4o-mini"
    fields: [secondary_outcomes, adverse_events, statistical_methods]
    confidence_threshold: 0.80
    
  tier_3_premium:
    model: "claude-3.5-sonnet"
    fields: [histopathology_classification, figure_interpretation]
    direct_route_conditions:
      - field_has_table_dependency
      - document_complexity > 0.8
```

## 3. Key Technical Components

### 3.1 PubMedFetcher (NEW - High Priority)

**Purpose:** Pre-fetch structured metadata before parsing PDF body.

```python
class PubMedFetcher:
    """Fetch structured abstracts and metadata via DOI."""
    
    async def fetch_by_doi(self, doi: str) -> Optional[PubMedRecord]:
        # 1. Query NCBI E-utilities
        # 2. Return structured abstract if available
        # 3. Return basic metadata (authors, journal, year) regardless
        pass
    
    def can_extract_from_abstract(self, record: PubMedRecord, fields: List[str]) -> List[str]:
        """Return list of fields extractable from structured abstract."""
        pass
```

**Expected Impact:** 20-30% fewer full PDF parses, 40-60% of fields from abstracts for well-structured papers.

### 3.2 Two-Pass Extraction Strategy (NEW)

**Purpose:** Minimize cloud API calls by doing cheap local pass first.

```python
async def two_pass_extraction(doc: Document, schema: Schema) -> ExtractionResult:
    # Pass 1: Local model, all fields, lenient confidence
    pass1 = await extract_all_fields(doc, schema, tier=Tier.LOCAL, mode="lenient")
    
    # Identify fields needing escalation
    low_confidence = [f for f in pass1 if f.confidence < 0.85]
    
    if not low_confidence:
        return pass1  # Early exit - no cloud calls needed!
    
    # Pass 2: Targeted cloud extraction for failures only
    for field in low_confidence:
        context = retrieve_field_specific_context(doc, field)
        pass2_result = await extract_single_field(context, field, tier=Tier.CLOUD)
        pass1.update(field.name, pass2_result)
    
    return pass1
```

**Expected Impact:** 30-40% reduction in cloud API calls.

### 3.3 Simplified Section Filtering

**Purpose:** Remove low-value content before tokenization.

```python
SECTIONS_TO_STRIP = [
    r"^references?\s*$",
    r"^acknowledgments?\s*$",
    r"^supplementary\s+materials?\s*$",
    r"^author\s+contributions?\s*$",
    r"^conflicts?\s+of\s+interest\s*$",
    r"^funding\s*$",
]

def filter_sections(parsed_doc: ParsedDocument) -> ParsedDocument:
    """Remove non-informative sections."""
    filtered_sections = []
    for section in parsed_doc.sections:
        if not any(re.match(pattern, section.title, re.I) for pattern in SECTIONS_TO_STRIP):
            filtered_sections.append(section)
    return parsed_doc.with_sections(filtered_sections)
```

**Expected Impact:** 15-25% token reduction.

### 3.4 Validation & Auto-Correction

```python
VALIDATION_RULES = {
    "sample_size": lambda x: 1 <= x <= 100000,
    "mean_age": lambda x: 0 <= x <= 120,
    "follow_up_months": lambda x: 0 <= x <= 600,
    "mortality_rate": lambda x: 0 <= x <= 1,
    "publication_year": lambda x: 1900 <= x <= 2026,
}

AUTO_CORRECTIONS = {
    "sample_size": [
        (r"l(\d+)", r"1\1"),      # OCR: l -> 1
        (r"O(\d+)", r"0\1"),      # OCR: O -> 0
        (r"(\d+),(\d{3})", r"\1\2"),  # Remove thousands separator
    ],
    "mortality_rate": [
        lambda x: x / 100 if x > 1 else x,  # Convert 45 to 0.45
    ],
}
```

### 3.5 Caching Strategy (Simplified)

**Single SQLite database with three tables:**

```sql
-- Document-level cache (skip re-parsing)
CREATE TABLE document_cache (
    doc_hash TEXT PRIMARY KEY,
    parsed_text TEXT,
    sections JSON,
    metadata JSON,
    parser_version TEXT,
    created_at TIMESTAMP
);

-- Field-level cache (skip re-extraction)
CREATE TABLE extraction_cache (
    doc_hash TEXT,
    field_name TEXT,
    schema_version INTEGER,
    result JSON,
    confidence REAL,
    tier_used INTEGER,
    tokens_used INTEGER,
    created_at TIMESTAMP,
    PRIMARY KEY (doc_hash, field_name, schema_version)
);

-- Embedding cache (skip re-embedding)
CREATE TABLE embedding_cache (
    chunk_hash TEXT PRIMARY KEY,
    embedding BLOB,
    model_name TEXT,
    created_at TIMESTAMP
);
```

**Invalidation Policy:** Simple and predictable.
- Document cache: Invalidate on parser version change
- Field cache: Invalidate on schema version change for that field
- Embedding cache: Invalidate on embedding model change

## 4. Resource Management

### 4.1 M4 MacBook Pro Limits

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Ollama Max VRAM | 14GB | Leave 10GB for OS + parsing |
| Concurrent Ollama Requests | 2 | M4 stays responsive |
| Context Window (Local) | 4096 tokens | Longer = slower |
| Quantization | Q4_K_M | Best quality/size balance |
| Parsing Workers | 3 (ProcessPool) | CPU-bound, not memory-bound |
| Extraction Workers | 4 (ThreadPool) | 2 local + 2 cloud async |

### 4.2 Ollama Configuration

```bash
# ~/.zshrc
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_KEEP_ALIVE=5m
```

### 4.3 Target Throughput

| Stage | Papers/Hour | Notes |
|-------|-------------|-------|
| Parsing | 20-30 | Docling is bottleneck |
| Local Extraction | 15-25 | Depends on field count |
| End-to-End (Hybrid) | 10-15 | Steady state |

### 3.6 Schema Chunking (NEW)

**Purpose:** Bypass LLM grammar complexity limits for massive clinical schemas.

- **Trigger:** Automatic detection for schemas > 30 fields.
- **Logic:** 124 fields → 5 sequential chunks of ~25 fields.
- **Workflow:** 
  1. Paper is sent 5 times with different sub-schemas.
  2. Sequential results are cached and merged.
  3. `extraction_confidence` is averaged across chunks.

### 3.7 CSV Schema Inference (NEW)

**Purpose:** Eliminate manual schema coding for new systematic reviews.

- **Input:** User's target data extraction template (CSV).
- **Inference:**
  - Column name → Field name.
  - Presence of data → Field type (int/float/text).
  - Optional `_quote` field injection for every data column.
- **CLI:** `python cli.py extract --schema template.csv`

## 4. Resource Management

# Hybrid Extraction Pipeline

> **Status:** Implemented in v2.0  
> **Components:** Phases 2-4 of Pipeline Optimization Track

## Overview

The hybrid extraction pipeline reduces cloud API costs by 40-60% through:
1. **Abstract-first extraction** - Extract metadata from PubMed before parsing
2. **Two-pass extraction** - Local LLM first, cloud only for failures
3. **Intelligent caching** - Skip re-processing identical documents
4. **Automated validation** - Catch and auto-correct common errors
5. **Recall Boost** - Proactively search for missing specific fields
6. **Semantic Chunking** - Smartly segment documents by topic using LLM anchors

## Quick Start

```python
from core.hierarchical_pipeline import HierarchicalExtractionPipeline

# Enable hybrid mode
pipeline = HierarchicalExtractionPipeline()
pipeline.set_hybrid_mode(True)  # Use local-first extraction
```

---

## Core Components

### AbstractFirstExtractor (`core/abstract_first_extractor.py`)

Extracts fields from structured PubMed abstracts before parsing the full PDF.

```python
from core.abstract_first_extractor import AbstractFirstExtractor
from core.pubmed_fetcher import PubMedFetcher

fetcher = PubMedFetcher()
article = fetcher.fetch_by_pmid("12345678")

extractor = AbstractFirstExtractor()
result = extractor.extract_from_abstract(article)
# Returns: doi, publication_year, journal_name, study_type, sample_size
```

**Extractable Fields:** DOI, publication year, journal, study type, sample size, age stats, follow-up duration

---

### TwoPassExtractor (`core/two_pass_extractor.py`)

Local-first extraction strategy minimizing cloud API calls.

```python
from core.two_pass_extractor import TwoPassExtractor

extractor = TwoPassExtractor(
    local_model="qwen3:14b",      # Primary local (Qwen3-14B)
    cloud_model="gpt-4o-mini",    # Escalation target
)

result = extractor.extract(
    context="Document text...",
    fields=["study_type", "sample_size"],
    confidence_threshold=0.85,
)

print(f"Cloud savings: {result.cloud_savings_ratio:.0%}")
```

**Tier Cascade:**
| Tier | Model | Use Case |
|------|-------|----------|
| 0 | Regex | DOI, year, sample size patterns |
| 1 | Qwen3-14B | Complex fields, local inference |
| 2 | gpt-4o-mini | Escalation for low confidence |
| 3 | claude-3.5-sonnet | Premium fields (histopathology) |

---

### SentenceExtractor (`core/sentence_extractor.py`)

**Status:** Phase B Complete

Implements "Unit-Context Extraction" to solve the "needle in a haystack" problem for complex fields. Splits documents into sentences and processes them naturally with sliding context windows (±2 sentences).

```python
from core.sentence_extractor import SentenceExtractor

extractor = SentenceExtractor()

# Process full document chunk-by-chunk
frames = await extractor.extract(chunks)
# Returns list of frames: [{"entity_text": "...", "attr": {...}}]
```

**Key Features:**
- **Sliding Window:** ±2 sentences context for disambiguation.
- **Async Concurrency:** Batch processes sentences for speed.
- **Hybrid Integration:** Automatically triggered for complex fields in `HierarchicalExtractionPipeline` when `hybrid_mode=True`.
- **Complex Fields:** `histopathology`, `immunohistochemistry`, `imaging_findings`, etc.

---

### CacheManager (`core/cache_manager.py`)

SQLite-based caching with automatic invalidation.

```python
from core.cache_manager import CacheManager

cache = CacheManager()

# Document-level caching
doc_hash = CacheManager.compute_doc_hash(pdf_text)
cache.set_document(doc_hash, parsed_text, metadata)

# Field-level caching
cache.set_field(doc_hash, "sample_size", {"value": 150}, schema_version=1, tier_used=1)

# Check stats
print(cache.get_stats())  # hit_rate, cached_documents, etc.
```

**Invalidation Rules:**
- Document cache → Parser version change
- Field cache → Schema version change
- Embedding cache → Model change

---

### ValidationRules (`core/validation_rules.py`)

Range checks, cross-field validation, and study-type-aware rules.

```python
from core.validation_rules import ValidationRules

validator = ValidationRules()

# Single field validation  
result = validator.validate_field("sample_size", 150)  # is_valid=True

# Cross-field checks
data = {"analyzed_n": 100, "enrolled_n": 150}
result = validator.validate_cross_field(data)  # Checks analyzed <= enrolled
```

**Built-in Range Rules:**
| Field | Range |
|-------|-------|
| `sample_size` | 1 - 100,000 |
| `mean_age` | 0 - 120 |
| `mortality_rate` | 0 - 1 |
| `follow_up_months` | 0 - 600 |

---

### AutoCorrector (`core/auto_corrector.py`)

Fixes common OCR and formatting errors.

```python
from core.auto_corrector import AutoCorrector

corrector = AutoCorrector()

# OCR fixes
result = corrector.correct("sample_size", "l50")  # → 150 (l→1)

# Percentage normalization
result = corrector.correct("mortality_rate", 45)  # → 0.45

# Bulk correction
corrected_data, corrections = corrector.correct_all(extracted_data)
```

**Automatic Fixes:**
- `l` → `1`, `O` → `0` (OCR errors)
- Remove thousands separators: `1,234` → `1234`
- Normalize percentages: `45` → `0.45` for rate fields

- Normalize percentages: `45` → `0.45` for rate fields

---

### Recall Boost (Phase C)

**Status:** Implemented

Proactively detects when required schema fields are missing (None/Empty) after an extraction pass. If found, it forces an additional pipeline iteration with a targeted prompt:
`"The following fields were missing or empty: [field]. Please review the text again specifically for these values."`

- **Penalty:** Applies a 10% score penalty to the incomplete result to encourage adopting the fuller result from the next iteration.
- **Loop Prevention:** Tracks requested fields to avoid infinite loops if data is genuinely missing.

---

### Semantic Chunking (Phase D)

**Status:** Implemented

Replace brittle regex/heuristic splitting with an LLM-based "Layout Analysis" step. The `SemanticChunker` scans the document text to identify logical sections tailored to scientific papers:
- **Methods**: Materials, Study Design, Statistical Analysis
- **Results**: Findings, Outcomes, Patient Characteristics
- **Discussion**: Limitations, Conclusions

**Mechanism:**
1. LLM scans text (first 30k chars) and returns JSON list of headers + anchor text.
2. Document is split *at* these anchor points.
3. Chunks are labeled (`section="Methods"`) used for targeted extraction queries.

**Usage:**
```python
# Create chunker
chunker = SemanticChunker(client=async_client)
# Chunk document
chunks = await chunker.chunk_document_async(full_text, doc_id="paper1")
# Result: [Chunk(section="Intro", text=...), Chunk(section="Methods", text=...)]
```

---

### Precise Provenance (Phase E)

**Status:** Implemented

Enables "Click-to-Source" functionality by tracking character-level indices for every extracted fact.
- **EvidenceFrame**: Core data structure capturing `text`, `doc_id`, `start_char`, `end_char`.
- **Integration**: The `SentenceExtractor` now returns these frames, allowing the pipeline to generate `EvidenceItem` objects with exact coordinates in the source text.

---

## Configuration

Field-to-tier routing is configured in `config/field_routing.yaml`:

```yaml
tier_1_standard:
  model: "qwen3:14b"
  confidence_threshold: 0.85
  fields:
    - inclusion_criteria
    - primary_outcome
    - intervention_description
```

---

## Test Commands

```bash
# All hybrid pipeline tests
pytest tests/test_abstract_first_extractor.py 
pytest tests/test_two_pass_extractor.py
pytest tests/test_phase4_components.py -v

# Full suite
pytest tests/ -q
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Cloud API Cost Reduction | ≥50% |
| Local Extraction Rate | ≥40% of fields |
| Cache Hit Rate | ≥80% (unchanged docs) |
| Accuracy Delta | <3% vs baseline |

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
from core.pipeline import HierarchicalExtractionPipeline
```

---

## Core Components

### TwoPassExtractor (`core/two_pass_extractor.py`)

Local-first extraction strategy minimizing cloud API calls.

```python
from core.two_pass_extractor import TwoPassExtractor

extractor = TwoPassExtractor(
    local_model="qwen3:14b",      # Primary local (Qwen3-14B)
    cloud_model="gpt-4o-mini",    # Escalation target
)
```

---

### SentenceExtractor (`core/sentence_extractor.py`)

**Status:** Active

Implements "Unit-Context Extraction" to solve the "needle in a haystack" problem for complex fields. Splits documents into sentences and processes them naturally with sliding context windows (±2 sentences).

```python
from core.sentence_extractor import SentenceExtractor

extractor = SentenceExtractor()
frames = await extractor.extract(chunks)
```

---

### CacheManager (`core/cache/manager.py`)

SQLite-based caching with automatic invalidation.

```python
from core.cache.manager import CacheManager
cache = CacheManager()
```

---

### Semantic Chunking (`core/semantic_chunker.py`)

**Status:** Active

Replace brittle regex/heuristic splitting with an LLM-based "Layout Analysis" step. The `SemanticChunker` scans the document text to identify logical sections tailored to scientific papers.

```python
from core.semantic_chunker import SemanticChunker
```

---

### Fuzzy Deduplicator (`core/fuzzy_deduplicator.py`)

**Status:** New in Phase 8

Removes near-duplicate text chunks to save tokens and improve quality.

```python
from core.fuzzy_deduplicator import FuzzyDeduplicator
deduplicator = FuzzyDeduplicator()
```

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

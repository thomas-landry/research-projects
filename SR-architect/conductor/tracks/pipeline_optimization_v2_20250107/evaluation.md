# Pipeline Optimization Evaluation Report

> **Generated:** 2025-01-07  
> **Scope:** Comprehensive review of SR-Architect extraction pipeline  
> **Objective:** Identify optimizations to reduce cost and latency while maintaining accuracy

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Bottleneck Analysis](#2-bottleneck-analysis)
3. [Token Optimization Strategies](#3-token-optimization-strategies)
4. [Model Selection & Routing](#4-model-selection--routing)
5. [Resource Management Strategy](#5-resource-management-strategy)
6. [Pipeline Modernization Recommendations](#6-pipeline-modernization-recommendations)
7. [Original Plan Critique](#7-original-plan-critique)
8. [Novel Optimization Ideas](#8-novel-optimization-ideas)
9. [Phase-by-Phase Recommendations](#9-phase-by-phase-recommendations)

---

## 1. Executive Summary

### Key Findings

1. **The original plan is over-engineered** for a <500 paper corpus. Reduced from 8 phases (57+ tasks) to 5 phases (~35 tasks) with equivalent functionality.

2. **High-impact missing feature:** PubMed/CrossRef metadata fetch could provide 20-30% token savings and wasn't in the original plan.

3. **Model recommendation:** Qwen 2.5 7B-Instruct (Q4_K_M) as primary local model, not Llama 3.1 8B, due to superior structured output adherence.

4. **Two-pass extraction strategy** is the highest-ROI change: cheap local pass first, targeted cloud escalation for failures only. Expected 30-40% cloud API reduction.

5. **Several planned components are low-ROI:** LayoutCleaner, FuzzyDeduplicator with MinHash, LLMLingua prompt compression, SchemaVersionControl.

### Projected Impact

| Metric | Current | Target | Confidence |
|--------|---------|--------|------------|
| Cloud API Cost | Baseline | -50% | High |
| Extraction Accuracy | Baseline | <3% delta | High |
| Pipeline Latency | Baseline | +30% max | Medium |
| Implementation Time | 12+ weeks | 5-7 weeks | High |

---

## 2. Bottleneck Analysis

### 2.1 Identified Bottlenecks

| Bottleneck | Stage | Impact | Root Cause |
|------------|-------|--------|------------|
| **PDF Parsing** | Pre-extraction | High latency | Docling accurate but slow; no parallel parsing |
| **Monolithic Chunking** | Retrieval | Token waste | Character-based splitting ignores document structure |
| **Serial Extraction** | Extraction | High latency | Fields extracted sequentially, not by complexity |
| **Redundant Context** | LLM Calls | Token waste | Full sections sent when field needs 1-2 sentences |
| **Validation Round-trips** | Post-extraction | Latency | Schema validation after extraction, not during |

### 2.2 Parallelization Opportunities

```
SAFE TO PARALLELIZE:
├── PDF Parsing (document-level) → ProcessPoolExecutor, max_workers=3-4
├── Metadata Fetch (PubMed/CrossRef) → Async IO, decouple from parsing
├── Field Extraction (independent fields within same tier)
│   ├── Tier 0 fields (regex) → All parallel
│   ├── Tier 1 fields (local) → Batch by complexity, 2-3 concurrent Ollama
│   └── Tier 2/3 fields (cloud) → Async API calls with rate limits
└── Validation (per-field) → Fully parallelizable

NOT SAFE (must be sequential):
├── Tier escalation (wait for lower tier result)
├── Cross-field validation (depends on multiple extractions)
└── Caching writes (need atomic updates)
```

**Expected Impact:** 40-60% latency reduction

### 2.3 Early-Exit Patterns

| Pattern | Trigger | Savings |
|---------|---------|---------|
| High-confidence short-circuit | Conf >0.95 on Tier 1 | 15-20% cloud calls |
| Schema-complete exit | All required fields done | 10-15% tokens |
| Document-type routing | Case report detected | 30-40% tokens |
| Abstract-first extraction | Structured abstract available | 50-70% tokens |

---

## 3. Token Optimization Strategies

### 3.1 Token Waste Sources

| Source | Waste Estimate | Mitigation |
|--------|----------------|------------|
| References section | 15-25% | Section filtering |
| Author affiliations | 5-10% | Section filtering |
| Figure/table captions (unneeded) | Variable | Context-aware retrieval |
| Repeated headers/footers | 2-5% | Deduplication |
| Boilerplate (copyright, etc.) | 2-3% | Regex stripping |

### 3.2 Pre-Processing Pipeline

```
Raw PDF
  │
  ├─► Section Detector (regex + heuristics)
  │     └─► Strip: References, Acknowledgments, Supplementary, Author Info
  │
  ├─► Boilerplate Remover
  │     └─► Strip: Copyright, journal headers, page numbers
  │
  ├─► Simple Deduplicator (hash-based, not MinHash)
  │     └─► Collapse repeated paragraphs
  │
  └─► Section-Aware Chunker
        └─► Chunk within sections, never across
```

### 3.3 Deterministic Extraction (Bypass LLM)

| Field | Method | Pattern |
|-------|--------|---------|
| DOI | Regex | `10\.\d{4,}/[^\s]+` |
| Publication Year | Regex | `(19\|20)\d{2}` in date context |
| Journal Name | PDF metadata | N/A |
| Sample Size | Regex + validation | `[Nn]\s*=\s*(\d+)` |
| Age (formatted) | Regex | `(\d+\.?\d*)\s*±\s*(\d+\.?\d*)\s*years?` |
| Sex ratio | Regex | `(\d+)\s*(male\|M).*(\d+)\s*(female\|F)` |

**Expected Impact:** 30-40% total token reduction

### 3.4 Caching Strategy

| Cache Level | Key | Invalidation | Use Case |
|-------------|-----|--------------|----------|
| Document Hash | `SHA256(PDF)` | Never (permanent) | Skip re-parsing |
| Parse Cache | `DocHash + ParserVersion` | Parser upgrade | Reuse parsed text |
| Field Cache | `DocHash + Field + SchemaVersion` | Schema change | Core extraction cache |
| Embedding Cache | `ChunkHash` | Model change | Avoid re-embedding |

**Implementation:** SQLite with JSON columns (portable, no external DB).

---

## 4. Model Selection & Routing

### 4.1 Local Model Comparison

| Model | VRAM (Q4) | Speed (tok/s) | Medical Accuracy | Structured Output | Recommendation |
|-------|-----------|---------------|------------------|-------------------|----------------|
| **Qwen 2.5 7B** | ~4.5GB | 40-50 | Good | **Excellent** | **Primary** |
| Llama 3.1 8B | ~5GB | 35-45 | Good | Good | Alternative |
| Mistral 7B v0.3 | ~4.5GB | 45-55 | Moderate | Good | Fast fallback |
| Phi-3.5 Mini | ~2.5GB | 60-80 | Moderate | Good | Lightweight tier |
| Llama 3.2 3B | ~2GB | 70-90 | Moderate | Moderate | Simple fields |

**Recommendation:** Qwen 2.5 7B-Instruct (Q4_K_M) as primary due to superior structured output adherence.

### 4.2 Field Routing Policy

```yaml
tier_0_regex:
  - doi, publication_year, journal_name
  - sample_size_raw (with validation)

tier_1_lightweight (Llama 3.2 3B):
  - study_type_simple, single_center_bool
  - prospective_bool, country

tier_1_standard (Qwen 2.5 7B):
  - inclusion_criteria, exclusion_criteria
  - primary_outcome, intervention_description
  - follow_up_duration, study_design_detailed

tier_2_cloud (gpt-4o-mini):
  - secondary_outcomes, adverse_events
  - subgroup_analyses, statistical_methods

tier_3_premium (claude-3.5-sonnet):
  - histopathology_classification
  - figure_interpretation
  - complex_eligibility_logic
```

### 4.3 Dynamic Routing Algorithm

```python
def compute_routing(field, doc_complexity, page_complexity, 
                    historical_accuracy, queue_depth) -> RoutingDecision:
    base_tier = field_config.default_tier
    
    # Escalate based on document complexity
    if doc_complexity > 0.7 and base_tier < TIER_LOCAL_STANDARD:
        base_tier = TIER_LOCAL_STANDARD
    if doc_complexity > 0.85 and base_tier < TIER_CLOUD_CHEAP:
        base_tier = TIER_CLOUD_CHEAP
    
    # Escalate based on page complexity (tables, figures)
    if page_complexity > 0.8 and base_tier < TIER_CLOUD_CHEAP:
        base_tier = TIER_CLOUD_CHEAP
    
    # Historical failure rate → start higher
    if historical_accuracy < 0.7 and base_tier < TIER_CLOUD_CHEAP:
        base_tier = TIER_CLOUD_CHEAP
    
    # Cloud queue saturated → try local first anyway
    if queue_depth > 20 and base_tier >= TIER_CLOUD_CHEAP:
        base_tier = max(TIER_LOCAL_STANDARD, base_tier - 1)
    
    return RoutingDecision(
        starting_tier=base_tier,
        confidence_threshold=field_config.threshold,
        use_self_consistency=field.is_numeric and field.is_critical
    )
```

---

## 5. Resource Management Strategy

### 5.1 M4 MacBook Pro Limits

| Parameter | Conservative | Aggressive |
|-----------|--------------|------------|
| Ollama Max VRAM | 14GB | 16GB |
| Concurrent Ollama Requests | 2 | 3 |
| Context Window (Local) | 4096 | 8192 |
| Quantization | Q4_K_M | Q4_K_S |
| Parsing Workers | 3 | 5 |

### 5.2 Ollama Configuration

```bash
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_KEEP_ALIVE=5m
```

### 5.3 Throughput Targets

| Stage | Papers/Hour |
|-------|-------------|
| Parsing | 20-30 |
| Local Extraction | 15-25 |
| End-to-End (Hybrid) | 10-15 |

### 5.4 Cloud Offload Decision Rule

```python
def should_offload_to_cloud(local_queue_depth, local_latency_ms,
                            local_failure_rate, remaining_papers,
                            deadline_hours) -> bool:
    # Rule 1: Local overwhelmed
    if local_queue_depth > 10 and remaining_papers > 20:
        return True
    
    # Rule 2: Local failing too often
    if local_failure_rate > 0.3:
        return True
    
    # Rule 3: Time pressure
    papers_per_hour_local = 3600_000 / local_latency_ms
    hours_needed = remaining_papers / papers_per_hour_local
    if hours_needed > deadline_hours * 0.8:
        return True
    
    return False
```

**Rule of Thumb:**
- <50 papers: Favor local
- 50-200 papers: Hybrid (local first, cloud for escalation)
- >200 papers with deadline: Cloud-first for complex fields

---

## 6. Pipeline Modernization Recommendations

### 6.1 Pre-Extraction

| Recommendation | Impact | Effort | Priority |
|----------------|--------|--------|----------|
| PubMed/CrossRef metadata fetch | 20-30% fewer parses | Low | **HIGH** |
| Document fingerprinting (simple hash) | Skip duplicates | Low | Medium |
| Stick with Docling → PyMuPDF4LLM fallback | Sufficient | Low | Medium |

### 6.2 Extraction

| Recommendation | Impact | Effort | Priority |
|----------------|--------|--------|----------|
| Two-pass extraction strategy | 30-40% fewer cloud calls | Medium | **HIGH** |
| Schema-aware prompts with few-shot | 10-15% accuracy boost | Medium | **HIGH** |
| Self-consistency for numeric fields | Better precision | Low | Medium |
| Static field routing (config file) | Simpler than dynamic | Low | Medium |

### 6.3 Post-Extraction

| Recommendation | Impact | Effort | Priority |
|----------------|--------|--------|----------|
| Validation rules (range, cross-field) | Catch 80% of errors | Low | **HIGH** |
| Auto-correction heuristics | Reduce re-extraction | Low | Medium |
| Manual review queue | Handle edge cases | Low | Medium |

---

## 7. Original Plan Critique

### 7.1 Low-ROI Tasks (Remove or Defer)

| Task | Phase | Issue | Recommendation |
|------|-------|-------|----------------|
| `LayoutCleaner` | 2 | Docling handles this | **REMOVE** |
| `TableExtractor` with pdfplumber | 2 | Over-engineered | **DEFER** - use vision if needed |
| `FuzzyDeduplicator` (MinHash) | 3 | Overkill for <500 papers | **SIMPLIFY** to hash |
| `ContextWindowMonitor` | 3 | Providers handle this | **REMOVE** |
| `IMRADParser` | 3 | Over-engineered | **SIMPLIFY** to regex |
| `SemanticChunker` | 3 | Section-based sufficient | **REMOVE** |
| `PromptCompressor` / LLMLingua | 4 | Marginal gains | **REMOVE** |
| `SchemaVersionControl` | 5 | Premature for <500 papers | **REMOVE** |
| `SchemaDiff` tool | 5 | Nice-to-have | **REMOVE** |
| A/B validation | 6 | Over-engineered | **SIMPLIFY** to spot-check |

### 7.2 Outdated Approaches

| Item | Issue | Modern Alternative |
|------|-------|-------------------|
| LLMLingua for compression | Adds complexity | Structured extraction |
| Separate LocalSummarizer | Adds latency | Abstract-first extraction |
| Circuit breaker (N failures) | Too coarse | Per-field failure tracking |

### 7.3 Missing High-Impact Items

| Item | Impact | Why Missing |
|------|--------|-------------|
| PubMed/CrossRef fetch | 20-30% savings | Not in original plan |
| Two-pass extraction | 30-40% cloud reduction | Not in original plan |
| Abstract-first extraction | 50-70% token savings | Not in original plan |

---

## 8. Novel Optimization Ideas

### 8.1 Vision-Model Table Extraction

**When:** Tables contain >30% of target data

```python
async def extract_from_table_image(table_image: bytes, 
                                   target_fields: List[str]) -> Dict:
    """Use vision model directly on table images."""
    response = await claude_vision_extract(
        image=table_image,
        prompt=f"Extract {target_fields} from this table",
        model="claude-3.5-sonnet"
    )
    return response
```

**Worth it when:** >50 papers with data in tables

### 8.2 Cross-Paper Pattern Mining

**When:** >100 papers, common patterns emerge

```python
def mine_extraction_patterns(successful_extractions, field, min_support=10):
    """Find common textual patterns for successful extractions."""
    patterns = []
    for e in successful_extractions:
        if e.field == field and e.confidence > 0.9:
            context = get_context_window(e.supporting_quote, window=50)
            patterns.append(context)
    
    clusters = cluster_by_similarity(patterns, threshold=0.8)
    return [get_centroid(c) for c in clusters if len(c) >= min_support]
```

**Worth it when:** >200 papers, accuracy plateaus

### 8.3 Active Learning for HITL Focus

**When:** Limited time for manual review

```python
def prioritize_for_review(extractions, budget=20):
    """Prioritize high-uncertainty, novel cases for review."""
    scored = []
    for e in extractions:
        score = (1 - e.confidence) * 3  # Uncertainty
        score += 2 if e.tier_disagreement else 0  # Disagreement
        score += (1 - e.pattern_similarity) * 2  # Novelty
        score += 1 if e.field in CRITICAL_FIELDS else 0
        scored.append((e, score))
    
    return sorted(scored, key=lambda x: -x[1])[:budget]
```

**Worth it when:** Manual review is bottleneck, >50 papers

---

## 9. Phase-by-Phase Recommendations

### Phase 0: POC Validation ✓
**Status:** Complete. Well-designed foundation.

### Phase 1: Resource Management ✓
**Status:** Complete. Simplification possible but not blocking.

### Phase 2: PDF Parsing

**High-leverage additions:**
1. **Add PubMedFetcher FIRST** - Highest ROI, missing from original
2. **Simplify fallback** - Docling → PyMuPDF4LLM only

**Remove:**
- LayoutCleaner (Docling handles it)
- Complex TableExtractor (defer)

### Phase 3: Local LLM & Chunking → Hybrid Extraction Core

**High-leverage changes:**
1. **Start with Qwen 2.5 7B** - Skip benchmarking if community data sufficient
2. **Implement two-pass extraction** - Biggest cloud cost reduction
3. **Static routing from config** - Dynamic routing is premature

**Remove:**
- IMRADParser (use regex)
- FuzzyDeduplicator (use simple hash)
- ContextWindowMonitor
- SemanticChunker

### Phase 4: Cascading → Caching & Validation

**Merge with caching, simplify:**
1. Simple SQLite cache (3 tables)
2. Validation rules (no LLM needed)
3. Auto-correction heuristics

**Remove:**
- PromptCompressor / LLMLingua
- Complex ModelCascader (static config sufficient)

### Phase 5: Caching → Integration & Docs

**Simplify:**
1. Single e2e test suite (not separate tier tests)
2. Manual spot-check (not A/B infrastructure)
3. Inline docs (not elaborate guides)

**Remove:**
- SchemaVersionControl
- SchemaDiff
- Troubleshooting decision tree

### Phases 6-7: Integration & Documentation

**Merge into Phase 5:**
- One comprehensive test
- Simple CLI flag
- Basic docs

---

## Appendix: Implementation Priority Matrix

| Item | Impact | Effort | Priority Score |
|------|--------|--------|----------------|
| PubMed/CrossRef fetch | High | Low | **9** |
| Two-pass extraction | High | Medium | **8** |
| Section filtering | Medium | Low | **7** |
| Qwen 2.5 7B setup | High | Low | **7** |
| Static field routing | Medium | Low | **7** |
| SQLite caching | Medium | Low | **6** |
| Validation rules | Medium | Low | **6** |
| Self-consistency voting | Medium | Low | **5** |
| Auto-correction | Low | Low | **4** |
| Manual review queue | Low | Low | **3** |

**Recommendation:** Implement in priority score order, top-down.

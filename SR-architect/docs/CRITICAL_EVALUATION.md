# SR-Architect: Critical Evaluation & Future Roadmap

A deep technical critique of the current implementation with actionable improvements.

---

## Part 1: How Data Extraction Currently Works

### The Current Flow

```
PDF → Docling Parser → Chunks → LLM (single pass) → Pydantic Model → CSV
```

**Step-by-step:**

1. **Parsing**: Docling converts PDF to structured document tree
2. **Section Identification**: Heuristic matching for "Abstract", "Methods", "Results"
3. **Context Assembly**: Concatenate relevant sections (max 15,000 chars)
4. **Single-Pass Extraction**: Send context + schema to LLM
5. **Validation**: Pydantic enforces types, Instructor retries on failure
6. **Output**: Write to CSV row

### Critical Weaknesses

#### 1. **Single-Pass Extraction is Fragile**

**Problem**: The LLM sees the entire context once and must extract all fields simultaneously. If a field is ambiguous or spread across sections, it may miss it.

**Example failure case**:
- Paper reports "mean age 52 ± 8 years" in Methods
- Paper also says "youngest patient was 34" in Results
- LLM must decide which to extract—often picks one arbitrarily

**Improvement**: Multi-pass extraction with field-specific prompts:
```python
# Pass 1: Demographics
demographics = extract(context, DemographicsSchema)

# Pass 2: Clinical findings (with demographics context)
clinical = extract(context, ClinicalSchema, prior_context=demographics)

# Pass 3: Outcomes
outcomes = extract(context, OutcomesSchema)
```

#### 2. **No Adaptive Schema Discovery**

**Problem**: User must define schema upfront. But systematic reviews often discover new variables during extraction ("Oh, several papers report smoking status—we should capture that").

**Current behavior**: Fixed schema → miss emerging patterns.

**Your proposed solution is correct**: The tool should learn from initial papers.

---

## Part 2: Adaptive Schema Discovery (Your Suggestion)

### Proposed Implementation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ADAPTIVE SCHEMA DISCOVERY                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                         │
│   │ Paper 1  │───▶│ DISCOVER │───▶│ Suggested│                         │
│   │ Paper 2  │    │  AGENT   │    │ Variables│                         │
│   │ Paper 3  │    │          │    │          │                         │
│   └──────────┘    └────┬─────┘    └────┬─────┘                         │
│                        │               │                                 │
│                        ▼               ▼                                 │
│                  ┌──────────────────────────┐                           │
│                  │   USER REVIEW & APPROVE  │                           │
│                  │   "Keep: age, sex, IHC"  │                           │
│                  │   "Add: smoking_status"  │                           │
│                  │   "Remove: funding"      │                           │
│                  └────────────┬─────────────┘                           │
│                               │                                          │
│                               ▼                                          │
│                  ┌──────────────────────────┐                           │
│                  │    FINALIZED SCHEMA      │───▶ Extract remaining     │
│                  └──────────────────────────┘      papers (77 more)     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Algorithm

```python
def adaptive_schema_discovery(papers: List[Path], sample_size: int = 3):
    """
    Phase 1: Discovery
    - Parse first N papers
    - Ask LLM: "What data points could be systematically extracted?"
    - Aggregate suggestions across papers
    - Rank by frequency and relevance
    
    Phase 2: User Review
    - Present suggested variables with examples
    - User approves, rejects, or modifies
    - User adds custom fields
    
    Phase 3: Extraction
    - Build final Pydantic model
    - Extract from ALL papers (including the 3 already parsed)
    """
    
    # Discovery prompt
    discovery_prompt = """
    You are analyzing academic papers for a systematic review.
    
    Read this paper and identify ALL data points that could be systematically 
    extracted and compared across multiple papers.
    
    For each data point, provide:
    - field_name: snake_case identifier
    - description: what this captures
    - data_type: text, integer, float, boolean, list
    - example_value: from this paper
    - extraction_difficulty: easy/medium/hard
    
    Focus on:
    - Patient demographics
    - Clinical presentations
    - Diagnostic methods
    - Treatment details
    - Outcomes
    - Study characteristics
    """
    
    all_suggestions = []
    for paper in papers[:sample_size]:
        doc = parser.parse_pdf(paper)
        suggestions = llm.extract(doc.full_text, SuggestedFieldsSchema)
        all_suggestions.extend(suggestions)
    
    # Aggregate and rank
    field_counts = Counter(s.field_name for s in all_suggestions)
    top_fields = [f for f, count in field_counts.most_common(20)]
    
    return top_fields, all_suggestions
```

### Benefits

1. **Captures heterogeneity**: Different papers report different things
2. **User remains in control**: Approve/reject before full extraction
3. **Reduces re-work**: Don't realize you need "smoking status" after extracting 50 papers
4. **Self-documenting**: The discovery log shows *why* each field was included

---

## Part 3: Dependency Critique

### Current Stack

| Dependency | Purpose | Critique |
|------------|---------|----------|
| `docling` | PDF parsing | **Heavy** (~500MB with models). Overkill for simple PDFs. No fallback. |
| `instructor` | Structured LLM | **Excellent choice**. Clean, well-maintained, provider-agnostic. |
| `chromadb` | Vectors | **Good for prototyping**. Not ideal for production (no backup/restore). |
| `pydantic` | Schemas | **Essential**. No critique. |
| `typer` | CLI | **Good**. Could use `click` for more complex flows. |
| `rich` | UI | **Good**. No issues. |
| `pandas` | CSV | **Acceptable**. Could stream writes instead. |

### Recommended Changes

#### 1. Add PyMuPDF as Fallback Parser

```python
try:
    from docling import DocumentConverter
    USE_DOCLING = True
except ImportError:
    import fitz  # PyMuPDF
    USE_DOCLING = False

def parse_pdf(path):
    if USE_DOCLING:
        return docling_parse(path)
    else:
        return pymupdf_parse(path)  # Simpler, faster, lighter
```

**Why**: Docling requires Python 3.10+, large downloads, and can fail on simple PDFs. PyMuPDF handles 80% of cases.

#### 2. Consider LanceDB Over ChromaDB

| Feature | ChromaDB | LanceDB |
|---------|----------|---------|
| Portability | SQLite file | Just a folder |
| Speed | Good | Faster (zero-copy) |
| Backup | Manual | cp -r |
| Dependencies | Many | Few |

Your original doc recommended LanceDB—it's actually better for the "funnel" use case.

#### 3. Add Streaming for Large Extractions

```python
# Instead of building full DataFrame in memory:
with open("results.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=schema_fields)
    writer.writeheader()
    
    for paper in papers:
        result = extract(paper)
        writer.writerow(result)  # Write immediately
```

---

## Part 4: Agent Brainstorming

### Current Agent: Extractor
Already implemented. Works but is "dumb"—no self-correction.

### Proposed Agents

#### Agent 1: Schema Discovery Agent
**Purpose**: Analyze sample papers, suggest extraction variables  
**Trigger**: First run on new corpus  
**Output**: Suggested FieldDefinition list  

```python
class SchemaDiscoveryAgent:
    """Analyzes papers to suggest extraction schema."""
    
    def discover(self, papers: List[ParsedDocument]) -> List[FieldDefinition]:
        suggestions = []
        for doc in papers:
            prompt = f"What systematic data points exist in this paper?"
            fields = self.llm.extract(doc.full_text, SuggestedFieldsSchema)
            suggestions.extend(fields)
        
        return self.dedupe_and_rank(suggestions)
```

#### Agent 2: Section Locator Agent
**Purpose**: Precisely identify where each data point lives  
**Why needed**: Current approach grabs "Methods" broadly—but age might be in "Participants" subsection  

```python
class SectionLocatorAgent:
    """Finds the exact section containing target information."""
    
    def locate(self, doc: ParsedDocument, field: str) -> str:
        prompt = f"""
        Which section of this paper contains information about: {field}
        
        Sections available:
        {[c.section for c in doc.chunks]}
        
        Return the section name and relevant quote.
        """
        return self.llm.extract(prompt, SectionLocationSchema)
```

#### Agent 3: Conflict Resolver Agent
**Purpose**: Handle contradictory information within a paper  
**Example**: Abstract says "52 patients", Table 1 shows 48 in analysis  

```python
class ConflictResolverAgent:
    """Resolves discrepancies in extracted data."""
    
    def resolve(self, field: str, values: List[str], sources: List[str]) -> str:
        prompt = f"""
        Multiple values found for {field}:
        {list(zip(values, sources))}
        
        Determine the correct value. Prefer:
        1. Tables over text
        2. Methods over Abstract
        3. More specific over general
        
        Return: chosen_value, reasoning
        """
        return self.llm.extract(prompt, ResolvedValueSchema)
```

#### Agent 4: Quality Auditor Agent
**Purpose**: Score extraction confidence, flag for human review  

```python
class QualityAuditorAgent:
    """Audits extraction quality."""
    
    def audit(self, extracted: dict, source_text: str) -> AuditReport:
        checks = []
        
        for field, value in extracted.items():
            quote = extracted.get(f"{field}_quote", "")
            
            # Check 1: Quote exists in source
            quote_found = quote in source_text
            
            # Check 2: Value derivable from quote
            derivable = self.llm.verify(f"Can '{value}' be derived from '{quote}'?")
            
            # Check 3: Consistency with other fields
            consistent = self.check_consistency(field, value, extracted)
            
            checks.append(FieldAudit(field, quote_found, derivable, consistent))
        
        return AuditReport(checks, overall_confidence=mean([c.score for c in checks]))
```

#### Agent 5: Meta-Analyst Agent
**Purpose**: After extraction, identify papers suitable for meta-analysis  

```python
class MetaAnalystAgent:
    """Determines meta-analysis feasibility."""
    
    def analyze(self, df: pd.DataFrame) -> MetaAnalysisReport:
        # Check for required fields
        has_effect_size = "effect_estimate" in df.columns
        has_ci = "confidence_interval" in df.columns
        has_n = "sample_size" in df.columns
        
        # Check heterogeneity
        interventions = df["intervention"].unique()
        outcomes = df["primary_outcome"].unique()
        
        return MetaAnalysisReport(
            feasible=has_effect_size and has_ci,
            poolable_subgroups=self.find_poolable_groups(df),
            heterogeneity_concerns=len(interventions) > 3,
            recommended_analysis="random_effects" if heterogeneous else "fixed_effects"
        )
```

---

## Part 5: Orchestration Improvements

### Current Orchestration: Linear Pipeline

```
Parse → Extract → Store → Output
```

**Problems**:
1. No parallelism
2. No checkpointing (crash = restart from zero)
3. No human-in-the-loop at critical points
4. No adaptive routing (all papers treated the same)

### Improved Orchestration: Stateful DAG

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         IMPROVED PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐                          │
│   │ SAMPLE  │────▶│DISCOVER │────▶│ REVIEW  │◀── Human approval        │
│   │ 3 PDFs  │     │ SCHEMA  │     │ SCHEMA  │                          │
│   └─────────┘     └─────────┘     └────┬────┘                          │
│                                        │                                 │
│                                        ▼                                 │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    PARALLEL EXTRACTION                           │   │
│   │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐       │   │
│   │  │P1  │ │P2  │ │P3  │ │P4  │ │P5  │ │... │ │P83 │ │P84 │       │   │
│   │  └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘       │   │
│   │     │      │      │      │      │      │      │      │          │   │
│   │     ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼          │   │
│   │  ┌─────────────────────────────────────────────────────────┐    │   │
│   │  │                   AUDIT CHECKPOINT                       │    │   │
│   │  │  confidence < 0.7 → HUMAN REVIEW QUEUE                  │    │   │
│   │  │  confidence ≥ 0.7 → AUTO-APPROVE                        │    │   │
│   │  └─────────────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                        │                                 │
│                                        ▼                                 │
│                              ┌─────────────────┐                        │
│                              │   SYNTHESIZE    │                        │
│                              │  + META-ANALYST │                        │
│                              └────────┬────────┘                        │
│                                       │                                  │
│                                       ▼                                  │
│                              ┌─────────────────┐                        │
│                              │   FINAL CSV +   │                        │
│                              │   AUDIT REPORT  │                        │
│                              └─────────────────┘                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Improvements

#### 1. Checkpointing with State Persistence

```python
import pickle

class PipelineState:
    def __init__(self, state_file: str = "pipeline_state.pkl"):
        self.state_file = state_file
        self.completed_papers = set()
        self.failed_papers = {}
        self.extracted_data = []
    
    def save(self):
        with open(self.state_file, "wb") as f:
            pickle.dump(self, f)
    
    @classmethod
    def load(cls, state_file: str):
        if Path(state_file).exists():
            with open(state_file, "rb") as f:
                return pickle.load(f)
        return cls(state_file)
    
    def should_process(self, paper: str) -> bool:
        return paper not in self.completed_papers
```

#### 2. Parallel Processing with ThreadPool

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_parallel(papers: List[Path], max_workers: int = 4):
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_single, p): p for p in papers}
        
        for future in as_completed(futures):
            paper = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                log_error(paper, e)
    
    return results
```

#### 3. Confidence-Based Routing

```python
def route_by_confidence(extracted: dict, threshold: float = 0.7):
    confidence = extracted.get("extraction_confidence", 0)
    
    if confidence >= threshold:
        return "auto_approve"
    elif confidence >= 0.4:
        return "human_review"  # Flag for manual check
    else:
        return "re_extract"  # Try with different prompt/model
```

---

## Part 6: Known Inefficiencies

### 1. **Redundant Parsing**
**Problem**: If extraction fails, we re-parse the PDF on retry.  
**Fix**: Cache parsed documents (pickle or JSON).

### 2. **No Batching for LLM Calls**
**Problem**: Each paper = separate API call = network overhead × 84.  
**Fix**: Batch 2-3 short papers per call (if context allows).

### 3. **Embedding Happens After Extraction**
**Problem**: We vectorize chunks after extraction, but we could do both in parallel.  
**Fix**: 
```python
with ThreadPoolExecutor() as executor:
    extraction_future = executor.submit(extract, doc)
    vectorization_future = executor.submit(vectorize, doc.chunks)
    
    extracted = extraction_future.result()
    vectors = vectorization_future.result()
```

### 4. **Schema Validation is Post-hoc**
**Problem**: Pydantic validates after LLM returns—if wrong, we retry.  
**Fix**: Use constrained decoding (Instructor's `max_retries=3` helps but isn't optimal).

### 5. **No Incremental Output**
**Problem**: User waits until all 84 papers complete to see any results.  
**Fix**: Stream results to CSV as each paper completes + live dashboard.

---

## Summary: Priority Improvements

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| 🔴 High | Adaptive schema discovery | Medium | Major |
| 🔴 High | Checkpointing/resume | Low | Major |
| 🟡 Medium | Parallel extraction | Low | Medium |
| 🟡 Medium | Confidence-based routing | Medium | Medium |
| 🟡 Medium | PyMuPDF fallback parser | Low | Medium |
| 🟢 Low | LanceDB migration | Medium | Low |
| 🟢 Low | Streaming CSV output | Low | Low |

---

## Next Steps

1. **Implement adaptive schema discovery** (highest value)
2. **Add checkpointing** (prevent lost work)
3. **Create human review queue** (flag low-confidence extractions)
4. **Test on 3 DPM papers** with current pipeline
5. **Iterate based on real extraction failures**

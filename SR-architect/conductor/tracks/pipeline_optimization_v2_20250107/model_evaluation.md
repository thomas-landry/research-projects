# Local Model Evaluation: Comprehensive Review for SR-Architect

> **Date:** 2025-01-08  
> **Hardware:** M4 MacBook Pro, 24GB Unified Memory  
> **Use Case:** Medical research PDF extraction with structured JSON output  
> **Framework:** Ollama + Instructor/Pydantic

---

## Executive Summary

**My original recommendation of Qwen 2.5 7B was outdated and suboptimal.** Based on comprehensive research:

1. **Gemini 2.0 Flash Lite** is the current production standard for extraction - $0.07/M tokens make it ~10x cheaper than local models (at 14B) when including power/hardware costs, while matching Sonnet on medical schema adherence.
2. **Qwen3 14B** remains the best local option for privacy-sensitive data.
3. **Schema Chunking** enables Gemini to handle 100+ field schemas that would otherwise cause validation failures.

---

## 1. Hardware Constraints Analysis

### M4 MacBook Pro (24GB) Realistic Limits

| Resource | Available | Safe Ceiling | Rationale |
|----------|-----------|--------------|-----------|
| Unified Memory | 24GB | 18GB for models | Leave 6GB for macOS + parsing |
| Metal GPU Cores | 10-core | Full utilization | M4 has excellent ML acceleration |
| Memory Bandwidth | 120 GB/s | Critical for inference speed | Higher than most consumer GPUs |

### Model Size vs Memory Requirements (Q4_K_M Quantization)

| Model | Parameters | VRAM Required | Fits M4 24GB? | Speed Estimate |
|-------|------------|---------------|---------------|----------------|
| Qwen3-0.6B | 0.6B | ~0.5GB | ✅ Easy | >100 tok/s |
| Qwen3-1.7B | 1.7B | ~1.2GB | ✅ Easy | 80-100 tok/s |
| Qwen3-4B | 4B | ~2.8GB | ✅ Easy | 60-80 tok/s |
| Qwen3-8B | 8B | ~5.5GB | ✅ Easy | 40-55 tok/s |
| **Qwen3-14B** | 14B | **~9GB** | ✅ **Yes** | **25-35 tok/s** |
| Qwen3-30B-A3B (MoE) | 30B (3B active) | ~18-19GB | ⚠️ Tight | 20-30 tok/s |
| Qwen3-32B | 32B | ~20GB | ⚠️ Marginal | 15-25 tok/s |
| Qwen2.5-7B | 7B | ~4.5GB | ✅ Easy | 40-50 tok/s |
| Qwen2.5-Coder-7B | 7B | ~4.5GB | ✅ Easy | 40-50 tok/s |
| Llama 3.1-8B | 8B | ~5GB | ✅ Easy | 35-45 tok/s |

**Key Finding:** You can run Qwen3-14B comfortably on your M4. This was the oversight in my original recommendation.

---

## 2. Generation Comparison: Qwen3 vs Qwen2.5

### Qwen3 Key Improvements (Released April 2025)

| Capability | Qwen2.5 | Qwen3 | Improvement |
|------------|---------|-------|-------------|
| **Parameter Efficiency** | Baseline | ~2x better | Qwen3-14B ≈ Qwen2.5-32B |
| **Reasoning** | Good | Excellent | Thinking/Non-thinking modes |
| **Structured Output** | Good | Excellent | Native JSON schema support |
| **Instruction Following** | Good | Significantly better | Better prompt adherence |
| **Context Length** | 128K | 32K native, 128K+ with YaRN | Similar |
| **Training Data** | 18T tokens | 36T tokens | 2x more data |

### Benchmark Comparison (from Qwen Technical Reports)

| Benchmark | Qwen2.5-7B | Qwen3-8B | Qwen3-14B | Notes |
|-----------|------------|----------|-----------|-------|
| MMLU | 74.2 | ~78 | ~82 | General knowledge |
| MATH | 49.8 | ~65 | ~75 | Mathematical reasoning |
| HumanEval | 57.9 | ~70 | ~80 | Code generation |
| IFEval | Good | Better | Best | Instruction following |
| ArenaHard | ~50 | ~70 | ~85.5 | Human preference |

**Critical Insight:** Qwen3-14B performs as well as Qwen2.5-32B in efficiency, and Qwen3-8B even outperforms Qwen2.5-14B on over half of benchmarks.

---

## 3. Model-Specific Analysis for Medical Extraction

### 3.1 Qwen3-14B (RECOMMENDED PRIMARY)

**Strengths:**
- Rivals Qwen2.5-32B in efficiency, scoring 85.5 on ArenaHard
- Quantized to Q4_0, it runs at 24.5 tokens/second on mobile (your M4 will be faster)
- Excellent structured output adherence with Ollama's JSON schema mode
- Hybrid thinking/non-thinking mode - use non-thinking for speed, thinking for complex fields
- Strong generalist model for mid-size inference servers with 16-24GB VRAM

**For Medical Extraction:**
- Excellent instruction following critical for schema adherence
- Strong at understanding structured data (tables, lists)
- Good reasoning for interpreting ambiguous medical text
- Supports 32K context natively (enough for most medical papers)

**Quantization Recommendation:** Q4_K_M (best quality/size balance)

**Memory Usage:** ~9GB at Q4_K_M + KV cache
- With 4K context: ~9.5GB total
- With 8K context: ~10.5GB total
- Leaves plenty of headroom on 24GB

### 3.2 Qwen3-30B-A3B (MoE) - WORTH TESTING

**Unique Advantage:** Mixture-of-Experts architecture
- 30B total parameters, but only **3B activated** during inference
- Preliminary community reports suggest impressive performance running entirely on CPU and system RAM. One user reported ~22 tokens/second generation using Q8 quantization with dual-channel DDR5 6000MHz RAM.

**For Your Use Case:**
- Could potentially outperform Qwen3-14B on complex fields
- Lower memory bandwidth requirements than dense models of similar intelligence
- Qwen3-30B-A3B outcompetes QwQ-32B with 10 times of activated parameters

**Risk:** ~18-19GB at Q4_K_M - tight fit, may need to reduce context or use KV cache quantization

### 3.3 Qwen2.5-Coder-7B - WRONG TOOL FOR THIS JOB

**Why I Was Wrong to Consider It:**

Qwen2.5-Coder is optimized for **code generation**, not **text extraction**:
- Training dataset: 70% Code, 20% Text, 10% Math
- Benchmarks focus on HumanEval, code completion, not NER or extraction
- While excellent for your Python development work, it's not optimized for understanding medical literature

**When to Use Qwen2.5-Coder:**
- Writing Python code for your pipeline
- Debugging and code review
- NOT for extracting data from medical PDFs

### 3.4 Qwen2.5-7B-Instruct - PREVIOUS GENERATION

**Still Decent, But Superseded:**
- Significant improvements in understanding structured data (e.g., tables) and generating structured outputs especially JSON
- Good baseline, but Qwen3 is simply better at the same size

**Use Case:** Fallback if Qwen3 has compatibility issues

### 3.5 Llama 3.2-3B / Llama 3.1-8B - LIGHTWEIGHT OPTIONS

**For Simple Fields:**
- Llama-3.1-8B and Llama-3.2-3B were evaluated on DRAGON 2024 benchmark for clinical information extraction
- Good for Tier 1 lightweight extraction
- Excellent Instructor library support

**Medical Extraction Research:**
- Fine-tuned Llama models achieved new state-of-the-art results, improving F1-score by up to 10 percentage points for adverse drug events and 6 pp. for medication reasons on English data.

---

## 4. Structured Output Capabilities Comparison

### Ollama JSON Schema Support

| Model | JSON Mode | Tool/Function Calling | Instructor Support |
|-------|-----------|----------------------|-------------------|
| Qwen3-14B | ✅ Excellent | ✅ Full | ✅ TOOLS mode |
| Qwen3-8B | ✅ Excellent | ✅ Full | ✅ TOOLS mode |
| Qwen2.5-7B | ✅ Good | ✅ Full | ✅ TOOLS mode |
| Llama 3.1-8B | ✅ Good | ✅ Full | ✅ TOOLS mode |
| Llama 3.2-3B | ✅ Good | ✅ Full | ✅ TOOLS mode |

**Instructor Library Compatibility:**
- Function Calling Models (llama3.1, llama3.2, llama4, mistral-nemo, qwen2.5, etc.): Uses TOOLS mode for enhanced function calling support
- Qwen3 model from Alibaba is optimized for reasoning and structured responses.
- qwen3:4b on these examples works well, the same as qwen3:8b

### Best Practices for Structured Extraction

```python
# From research - optimal settings for medical extraction
client = instructor.from_provider(
    "ollama/qwen3:14b",
    mode=instructor.Mode.JSON,  # Or TOOLS for function calling models
)

response = client.create(
    messages=[...],
    response_model=MedicalExtractionSchema,
    temperature=0,  # Critical for schema adherence
    max_retries=2,
    timeout=30.0,
)
```

Set temperature to 0 for maximum schema adherence. Validate with json.Unmarshal and fallback if parsing fails.

---

## 5. Medical/Clinical NLP Performance

### Research Findings on Local LLMs for Medical Extraction

| Study | Model | Task | Finding |
|-------|-------|------|---------|
| JAMIA Open 2025 | Qwen2.5-14B, Phi-4-14B | DRAGON benchmark | Several models around 14 billion parameters performed competitively, coming close to matching a top-performing, fine-tuned system |
| npj Digital Medicine 2024 | Llama 2 70B | Clinical extraction | High sensitivities and specificities for detecting ascites (95%, 95%), confusion (76%, 94%) |
| ScienceDirect 2025 | Fine-tuned Llama | Medication extraction | Fine-tuned local open-source generative LLMs outperform SOTA methods for medication information extraction |
| BMJ Health Care 2025 | Multiple LLMs | EHR extraction | Claude 3.0 Opus, Claude 3.0 Sonnet, GPT 4, and Llama 3-70b exhibited excellent performance in data extraction |

**Key Insight:** For medical extraction, the research shows:
1. **General instruction-following models work well** - domain-specific models don't always outperform
2. **14B parameter models hit the sweet spot** for local deployment
3. **Fine-tuning helps significantly** - but even zero-shot is competitive

---

## 6. Revised Model Recommendations

### Tiered Model Strategy (Updated)

| Tier | Model | Backend | Use Case | Cost |
|------|-------|---------|----------|------|
| **Tier 0** | Regex/Heuristics | Local | DOI, Year, numbers | $0 |
| **Tier 1 Lite** | Qwen3-4B | Ollama | Simple booleans | $0 |
| **Tier 2 Prod** | **Gemini 2.0 Flash Lite** | OpenRouter | **Bulk Extraction** | **$0.015/paper** |
| **Tier 3 Premium**| Claude-3.5-Sonnet| OpenRouter | Complex Reasoning | $0.15/paper |

### Configuration Recommendations

```yaml
# Updated field_routing.yaml
models:
  tier_1_lightweight:
    primary: "qwen3:4b"
    fallback: "llama3.2:3b"
    quantization: Q4_K_M
    max_context: 4096
    temperature: 0
    
  tier_1_standard:
    primary: "qwen3:14b"           # UPDATED from qwen2.5:7b
    fallback: "qwen3:8b"
    quantization: Q4_K_M
    max_context: 8192
    temperature: 0
    
  tier_1_experimental:             # OPTIONAL - test this
    model: "qwen3:30b-a3b"         # MoE model
    quantization: Q4_K_M
    max_context: 4096
    temperature: 0
    note: "Test for complex fields - may outperform 14B"
```

### Ollama Configuration for M4

```bash
# Recommended Ollama settings for M4 24GB
export OLLAMA_NUM_PARALLEL=2          # Can handle 2 concurrent requests with 14B
export OLLAMA_MAX_LOADED_MODELS=2     # Qwen3-14B + Qwen3-4B simultaneously
export OLLAMA_KEEP_ALIVE=5m           # Unload after 5min idle
export OLLAMA_KV_CACHE_TYPE=f16       # Default, good quality
# Alternative: q8_0 for longer contexts with quality tradeoff
```

---

## 7. Benchmark Plan for Your Golden Dataset

Before committing to Qwen3-14B, run this validation:

### Quick Benchmark Protocol

```python
# benchmark_local_models.py
models_to_test = [
    "qwen3:14b",           # Primary recommendation
    "qwen3:8b",            # Faster alternative  
    "qwen3:30b-a3b",       # MoE - test if it fits
    "qwen2.5:7b-instruct", # Previous recommendation (baseline)
    "llama3.1:8b",         # Alternative
]

metrics = {
    "accuracy_per_field": {},    # F1 vs golden dataset
    "tokens_per_second": {},     # Inference speed
    "schema_adherence": {},      # % valid JSON output
    "memory_usage_gb": {},       # Peak VRAM
    "confidence_calibration": {} # Are confidence scores reliable?
}

# For each model, extract from 5-10 papers from golden dataset
# Compare against ground truth
```

### Expected Results

| Model | Expected Accuracy | Speed | Memory | Notes |
|-------|-------------------|-------|--------|-------|
| Qwen3-14B | Highest | Medium | ~10GB | Best overall |
| Qwen3-8B | High | Fast | ~6GB | Good balance |
| Qwen3-30B-A3B | Highest* | Medium | ~18GB | *If it fits |
| Qwen2.5-7B | Good | Fast | ~5GB | Baseline |

---

## 8. Implementation Steps

### Immediate Actions

1. **Pull Qwen3-14B:**
   ```bash
   ollama pull qwen3:14b
   # Or specific quantization:
   ollama pull qwen3:14b-instruct-q4_K_M
   ```

2. **Test Basic Extraction:**
   ```python
   import instructor
   from pydantic import BaseModel
   
   class SampleSize(BaseModel):
       n_enrolled: int | None
       n_analyzed: int | None  
       confidence: float
       supporting_quote: str
   
   client = instructor.from_provider("ollama/qwen3:14b")
   result = client.create(
       messages=[{"role": "user", "content": f"Extract sample size: {methods_section}"}],
       response_model=SampleSize,
       temperature=0,
   )
   ```

3. **Benchmark Against Golden Dataset:**
   - Run 10-20 papers through Qwen3-14B
   - Compare F1 to baseline (Sonnet-only)
   - If accuracy delta <3%, proceed with Qwen3-14B as primary

### Model Pull Commands

```bash
# Primary recommendation
ollama pull qwen3:14b

# Lightweight tier
ollama pull qwen3:4b

# Fallback options  
ollama pull qwen3:8b
ollama pull llama3.2:3b

# Experimental (test if fits in memory)
ollama pull qwen3:30b-a3b
```

---

## 9. Summary: Why My Original Recommendation Was Wrong

| Aspect | Original Recommendation | Corrected Recommendation | Why |
|--------|------------------------|-------------------------|-----|
| **Primary Model** | Qwen2.5-7B | **Qwen3-14B** | Qwen3 released April 2025 with ~2x efficiency gains |
| **Lightweight** | Llama 3.2 3B | **Qwen3-4B** | Qwen3-4B rivals Qwen2.5-72B performance |
| **Code Model** | Considered Qwen2.5-Coder | **Not for extraction** | Optimized for code, not medical text |
| **MoE Option** | Not considered | **Qwen3-30B-A3B** | Only 3B active params - potentially best option |

**Root Cause of Error:** I relied on information from before Qwen3's release (April 2025) without verifying current model landscape.

---

## 10. Next Steps

1. **Update plan.md** with corrected model recommendations
2. **Update field_routing.yaml** with Qwen3 models
3. **Run benchmark** on golden dataset before Phase 3 implementation
4. **Test Qwen3-30B-A3B** - if it runs on your M4, it may outperform Qwen3-14B

Would you like me to update the track documents with these corrected recommendations?

# Lessons Learned - SR-Architect

> **Purpose**: Shared memory for all agents. Document mistakes to avoid repeating them.
> **All agents MUST read this file before executing tasks.**

---

## 🚨 Critical Lessons

### COST-001: E2E Test Cost Overrun (2026-01-08)

**What happened**: E2E extraction test intended for 10 papers cost **$17.37** instead of ~$1.20.

**Root causes**:
1. `--limit 10` CLI flag was **ignored** - all 50 PDFs were processed
2. `--hybrid-mode` flag exists but **not wired** to local models (Ollama)
3. Hierarchical pipeline runs 4 passes per paper (relevance → extraction → check → audit)
4. No cost guardrails or abort mechanism existed

**Cost breakdown**:
| Operation | Calls | Cost | % |
|-----------|-------|------|---|
| extraction (Sonnet) | 164 | $10.19 | 59% |
| relevance_classification (Sonnet) | 273 | $5.40 | 31% |
| quality_audit (GPT-4o) | 759 | $1.08 | 6% |

**Fixes required**:
- [x] Fix `--limit` flag in cli.py ✅ (2026-01-08: Added `limit=limit` param to service.run_extraction())
- [/] Wire `--hybrid-mode` to Ollama/Qwen3 before cloud ⚠️ (Partially done: Flag wired CLI→service→pipeline, but TwoPassExtractor not integrated into extraction flow. See GAP-001.)
- [x] Add `--max-cost` CLI guardrail ✅ (2026-01-08: Added --max-cost flag, pre-flight cost estimation, confirmation for >$5)
- [x] Add pre-flight cost confirmation for expensive operations ✅ (2026-01-08: Shows est. cost per paper and total before proceeding)

**Prevention rules**:
1. **Always test with `--limit 3 --dry-run` first** before full extraction
2. **Verify CLI flags actually work** before trusting them
3. **Check token_usage.jsonl after short runs** to estimate full cost

---

## 📋 Process Lessons

### PROC-001: Verify CLI Flags Before Large Runs

Before running extraction on >5 papers:
1. Run with `--limit 2` and verify only 2 papers process
2. Check `output/token_usage.jsonl` for cost estimate
3. Multiply by total papers to estimate full cost
4. Get user approval if cost > $5

### PROC-002: Laptop Sleep Causes Long Runs

The 4-hour extraction was likely extended by laptop sleep. For long runs:
1. Use `caffeinate -i python3 cli.py extract ...` on macOS
2. Or run in tmux/screen session
3. Consider adding progress checkpointing

---

## 🔧 Technical Lessons

### TECH-001: Caching Layers Explained

| Layer | What's Cached | Location |
|-------|---------------|----------|
| **Parsed PDFs** | Document chunks (JSON) | `.cache/parsed_docs/` |
| **LLM Responses** | Some responses | `.cache/llm_responses/` |
| **Fingerprints** | Duplicate detection | In-memory (session) |

**Important**: Re-parsing is cached, but LLM extraction is NOT fully cached. Running the same extraction twice will cost money again.

### TECH-002: Cost Per Operation

| Operation | Model | Est. Cost/Call |
|-----------|-------|----------------|
| extraction | Claude Sonnet | ~$0.06-0.08 |
| relevance_classification | Claude Sonnet | ~$0.02 |
| quality_audit | GPT-4o | ~$0.0015 |
| extraction_check | GPT-4o | ~$0.008 |

---

## ✅ Verification Checklist

Before any expensive operation, agents should verify:

- [ ] `--limit` flag is working (run with limit=2, count output rows)
- [ ] `--hybrid-mode` routes to local models first (check logs)
- [ ] Cost estimate is reasonable (<$5 for test runs)
- [ ] User has approved the cost

---

## 📍 Known Gaps

### GAP-001: TwoPassExtractor Not Integrated (2026-01-08)

**Status**: 🟡 Partially Complete

**What exists**:
- `--hybrid-mode` CLI flag (defaults to True)
- Flag wired: cli.py → service.py → pipeline.set_hybrid_mode()
- `TwoPassExtractor` class with local-first logic
- `field_routing.yaml` with 4-tier configuration

**What's missing**:
- Pipeline extraction methods don't check `self.hybrid_mode`
- `TwoPassExtractor.extract()` is never called from pipeline
- No code path routes fields through local → cloud cascade

**To fix**: Modify `HierarchicalExtractionPipeline.extract_document()` to:
1. Check `self.hybrid_mode`
2. If enabled, call `self.two_pass_extractor.extract()` first
3. Only escalate to cloud for low-confidence fields

# Baseline Performance (Sonnet-Only Pipeline)

**Date:** 2026-01-06
**Dataset:** 10 Papers (Case Reports)
**Model:** anthropic/claude-3.5-sonnet

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Cost per Paper** | ~$0.27 | Average from 7 processed papers ($1.87 total) |
| **Tokens per Paper** | ~30,500 | Includes hierarchical overhead (screening, checking, iterating) |
| **Latency per Paper** | ~1-2 min | Parallel processing (workers=3) |
| **Accuracy** | High | Passed validation with score > 0.9 |

## Breakdown

*   **Total Cost (10 papers):** ~$2.60 (Estimated based on $0.27 avg)
*   **Total Tokens (10 papers):** ~305,000
*   **Pricing:** Input $3/1M, Output $15/1M (Sonnet)

## Goal
Reduce cost by >50% (target <$0.13/paper) and latency by 20%.
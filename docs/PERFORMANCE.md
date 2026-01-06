# Performance Benchmarks

> **Measured:** January 6, 2026 on Ubuntu 24.04 with OpenAI API (gpt-5-nano, gpt-5-mini)

## Measured LLM Response Times

Data extracted from container logs (`LLM_RESPONSE duration_ms`):

| Model | Calls | p50 | p95 | Min | Max | Avg |
|-------|-------|-----|-----|-----|-----|-----|
| gpt-5-nano | 43 | 11.3s | 17.2s | 5.0s | 17.9s | 11.0s |
| gpt-5-mini | 158 | 24.0s | 46.4s | 1.2s | 58.4s | 26.6s |
| **Total** | **207** | - | - | - | - | - |

## Actual Cost

| Metric | Value |
|--------|-------|
| Total LLM calls | 207 |
| Total spend | **$0.67** |
| Avg cost/call | $0.0032 |

**Note:** Cost includes initial backfill of 200 papers (77 accepted, 74 analyzed).

## Filter Performance

| Metric | Measured |
|--------|----------|
| Papers fetched | 200 |
| Papers accepted (filter) | 77 (38.5%) |
| Papers analyzed (full pipeline) | 74 |
| Duplicates skipped | 103 |
| Marked speculative/irrelevant | 44 |

## Processing Summary

| Stage | Model | Avg Time |
|-------|-------|----------|
| Regex pre-filter | Local | <100ms |
| FilterAgent | gpt-5-nano | ~11s |
| ExtractionAgent | gpt-5-mini | ~27s |
| CriticAgent | gpt-5-mini | ~27s |

**End-to-end per paper:** ~60-90s (when all stages run)

## Comparison: OpenAI vs Ollama

| Metric | OpenAI (measured) | Ollama (estimated) |
|--------|-------------------|-------------------|
| Filter time | 11s (p50) | 30-60s |
| Extraction time | 27s (p50) | 45-90s |
| Speed advantage | **Baseline** | ~3x slower |
| Cost | $0.67 for 200 papers | $0 + power |

**Recommendation:** Use OpenAI for speed. Use Ollama for air-gapped/privacy deployments.

## Resource Usage

| Service | Memory |
|---------|--------|
| Redis | ~50MB |
| ingestion_service | ~150MB |
| agent_core | ~200MB |
| dashboard | ~250MB |
| **Total** | **~650MB** |

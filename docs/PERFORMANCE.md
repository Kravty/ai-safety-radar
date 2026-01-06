# Performance Benchmarks

## Current Configuration

| Component | Model | Provider |
|-----------|-------|----------|
| FilterAgent | gpt-5-nano | OpenAI |
| ExtractionAgent | gpt-5-mini | OpenAI |
| CriticAgent | gpt-5-mini | OpenAI |
| CuratorAgent | gpt-5-mini | OpenAI |

## Processing Times

### Per-Paper Timing

| Stage | Time | Notes |
|-------|------|-------|
| Regex pre-filter | <100ms | Local, no API call |
| FilterAgent (gpt-5-nano) | 3-8s | When LLM validation needed |
| ExtractionAgent (gpt-5-mini) | 5-15s | Structured output |
| CriticAgent (gpt-5-mini) | 3-8s | Validation pass |
| **Total per paper** | **15-30s** | End-to-end |

### Batch Processing

| Batch Size | Duration | Notes |
|------------|----------|-------|
| 50 papers | ~5 min | Smoke test |
| 100 papers | ~10 min | Standard backfill |
| 200 papers | ~15 min | Full backfill |

## Filter Performance

### Two-Stage Filter Savings

| Metric | Value |
|--------|-------|
| Papers handled by regex alone | ~60% |
| Papers requiring LLM validation | ~40% |
| **API call reduction** | **60%** |

### Acceptance Rates

| Filter Mode | Acceptance Rate | Use Case |
|-------------|----------------|----------|
| Permissive | 50-60% | Broad monitoring |
| Balanced | 35-45% | **Recommended** |
| Strict | 15-25% | Top papers only |

**Current setting:** Balanced (38% observed)

## Cost Analysis

### Per-Operation Costs (gpt-5-nano/mini)

| Operation | Est. Cost | Volume/Month |
|-----------|-----------|--------------|
| Filter (gpt-5-nano) | $0.0001/paper | 120 papers |
| Extraction (gpt-5-mini) | $0.001/paper | 45 papers |
| Critic (gpt-5-mini) | $0.0005/paper | 45 papers |
| Curator (gpt-5-mini) | $0.002/digest | 4 digests |

### Monthly Cost Estimate

Assuming weekly ingestion (30 papers × 4 weeks = 120 papers/month), 38% acceptance:

| Component | Monthly Cost |
|-----------|--------------|
| Filtering | $0.012 |
| Extraction | $0.045 |
| Critic | $0.023 |
| Curator | $0.008 |
| **Total** | **~$0.09/month** |
| **Annual** | **~$1.08/year** |

## Backfill Benchmarks

### Observed Results (60-day backfill)

```
📊 BACKFILL SUMMARY
============================================================
  Fetched:         200 papers
  Accepted:        77 papers (38.5%)
  Rejected:        123 papers
  Duration:        15.0 minutes
  Papers Analyzed: 35+
============================================================
```

### Estimated Backfill Times

| Period | Papers | Filter Time | Analysis Time | Total |
|--------|--------|-------------|---------------|-------|
| 30 days | ~100 | 5 min | 10 min | ~15 min |
| 60 days | ~200 | 10 min | 15 min | ~25 min |
| 90 days | ~300 | 15 min | 25 min | ~40 min |

## Resource Usage

### Container Memory

| Service | Memory | Notes |
|---------|--------|-------|
| Redis | ~50MB | With AOF enabled |
| ingestion_service | ~150MB | Python + httpx |
| agent_core | ~200MB | Python + instructor |
| dashboard | ~250MB | Streamlit |
| **Total** | **~650MB** | All services |

### Network

| Flow | Bandwidth | Notes |
|------|-----------|-------|
| ArXiv fetch | ~1MB/batch | Paper metadata only |
| OpenAI API | ~10KB/request | JSON payloads |
| Redis internal | Minimal | Local network |

## Comparison: OpenAI vs Ollama (Jetson)

| Metric | OpenAI (gpt-5-mini) | Ollama (ministral-3:8b) |
|--------|---------------------|-------------------------|
| Filter time | 3-8s | 30-60s |
| Extraction time | 5-15s | 45-90s |
| Total per paper | 15-30s | 2-5 min |
| Monthly cost | ~$0.09 | $0 (+ power) |
| Setup complexity | Low | High |
| Privacy | Cloud | Local |

**Recommendation:** Use OpenAI for speed and simplicity. Use Ollama for air-gapped/privacy requirements.

## Optimization Tips

1. **Increase regex thresholds** — More auto-accept/reject = fewer API calls
2. **Batch backfills** — Run during off-peak hours
3. **Monitor acceptance rate** — Target 35-45% for balanced coverage
4. **Use gpt-5-nano for filtering** — Cheaper than gpt-5-mini, sufficient quality

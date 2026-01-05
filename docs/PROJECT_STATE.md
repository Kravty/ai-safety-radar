# Project State - January 5, 2026

## Executive Summary

**Project Goal:** AI Security research news aggregator  
**Current Status:** 🟢 FUNCTIONAL - ArXiv papers being ingested and processed  
**Completion:** ~85% (ingestion pipeline fixed, papers being analyzed)

---

## What Works ✅

### Dashboard
- ✅ Streamlit UI displaying threat landscape
- ✅ Real-time metrics (pending count, analyzed count)
- ✅ Agent status monitoring (polling/processing toggle)
- ✅ Severity distribution visualization
- ✅ Manual controls (trigger ingestion, process queue)

### Infrastructure
- ✅ Redis Streams for job queueing
- ✅ Consumer groups for reliable processing
- ✅ Forensic logging (audit trail)
- ✅ Podman containerization
- ✅ Air-gapped architecture (security)

### Agent Core
- ✅ Content-based deduplication (prevents semantic duplicates)
- ✅ Multi-agent analysis pipeline (FilterAgent, ExtractionAgent, CriticAgent, CuratorAgent)
- ✅ Status updates (visible in dashboard)
- ✅ Error handling and ACK logic

### Ingestion Pipeline (FIXED 2026-01-05)
- ✅ ArXiv papers fetched (10 per cycle)
- ✅ FilterAgent with LLM analyzing papers
- ✅ Papers accepted with confidence scores
- ✅ NEW log format showing reasoning

---

## Recent Fix: Ingestion Pipeline (2026-01-05)

### Problem Was:
Containers running stale code despite source changes.

### Fix Applied:
```bash
podman-compose down
podman-compose build --no-cache ingestion_service
podman-compose build --no-cache agent_core
podman-compose up -d
```

### Evidence of Fix:
```
INFO:__main__:  ✅ ACCEPTED (confidence: 0.97)
INFO:__main__:     Reasoning: 1. **Safety-Relevant Keywords Identified**...
INFO:__main__:  ✅ ACCEPTED (confidence: 0.98)
```

### Current Metrics:
- Pending papers: 10
- Analyzed papers: 3
- All 4 containers running healthy

---

## What Needs Improvement 🟡

### Performance
- LLM calls are slow (~30-60s per paper with ministral-3:8b on Jetson)
- Consider batching or caching for repeated queries

### Minor Issues
- Pydantic deprecation warning for `class Config` (should use `ConfigDict`)
- `datetime.utcnow()` deprecation (non-critical)

---

## Architecture

### Data Flow

```
ArXiv API → Ingestion Service → papers:pending → Agent Core → papers:analyzed → Dashboard
            (FilterAgent?)        (Redis Stream)  (FilterAgent)    (Redis Stream)
```

**Current Bottleneck:** Ingestion Service (0 papers queued)

### AI Agents

1. **FilterAgent** - Determines if paper is AI Security relevant
   - Model: ministral-3:8b (Ollama on Jetson)
   - Status: 🔴 Either not being called OR too conservative

2. **ExtractionAgent** - Extracts threat details from paper
   - Model: ministral-3:8b
   - Status: ✅ Working (tested with manual papers)

3. **CriticAgent** - Validates extraction quality
   - Model: ministral-3:8b
   - Status: ✅ Working

4. **CuratorAgent** - Generates weekly digest
   - Model: ministral-3:8b
   - Status: ✅ Working (triggered after N papers)

---

## Key Metrics (Current)

- **Papers Analyzed:** 2 (both manual test data)
- **ArXiv Papers:** 0
- **Papers from 2025-2026:** 0
- **Dashboard Uptime:** 100%
- **Agent Core Uptime:** 100%
- **Ingestion Success Rate:** 0%

---

## Code Quality Status

### Agent Standardization (Updated 2026-01-05)

**All agents now follow Instructor + Pydantic v2 best practices:**

- ✅ **FilterAgent**: Uses Instructor + Pydantic v2 (already compliant)
- ✅ **ExtractionAgent**: Refactored to use Instructor + Pydantic v2 (2026-01-05)
- ✅ **CriticAgent**: Uses Instructor + Pydantic v2 (already compliant)
- ✅ **CuratorAgent**: Uses Instructor + Pydantic v2 (already compliant)

**Benefits Achieved:**
- Type-safe LLM responses with automatic validation
- Automatic retry on validation errors (Instructor feature)
- Reduced code complexity (ExtractionAgent: 122→118 lines, cleaner)
- Consistent patterns across all agents
- Better error messages and debugging
- Compatible with ministral-3:8b (8B local model)

**Model Improvements:**
- ✅ ThreatSignature model now has Pydantic validator for severity field
- ✅ Accepts both string ("Critical", "High") and int (1-5) formats
- ✅ Automatic conversion handled by Pydantic v2 `@field_validator`

---

## Technical Debt

1. **Unclear Filtering Logic** (CRITICAL)
   - Code changes made but not reflected in running containers
   - Logs show OLD rejection format, not new LLM reasoning
   - Container rebuild may be required

2. **Deployment Verification**
   - `podman-compose restart` may not reload volume-mounted code
   - Need explicit `podman-compose down && up` or rebuild

3. **ArXiv Query**
   - Current query may be too narrow
   - Only fetches 10 papers (configurable via ARXIV_MAX_RESULTS)

4. **LLMClient chat() method** (OPTIONAL)
   - `chat()` method in LLMClient now unused after ExtractionAgent refactor
   - Consider removing or keeping for future flexibility

---

## Next Agent Priorities

### PRIORITY 1: Verify Deployment

```bash
# Full rebuild
podman-compose down
podman-compose build ingestion_service
podman-compose up -d

# Verify NEW code is running
podman exec ai-safety-radar_ingestion_service_1 \
  cat /app/src/ai_safety_radar/scripts/run_ingestion_service.py | head -30

# Should see: from ai_safety_radar.agents.filter_agent import FilterAgent
# Should NOT see: SECURITY_PAPER_INDICATORS = {...}
```

### PRIORITY 2: Verify FilterAgent Called

```bash
# Trigger ingestion
podman exec ai-safety-radar_redis_1 redis-cli PUBLISH agent:trigger ingest

# Watch logs
podman logs -f ai-safety-radar_ingestion_service_1

# Look for: "Calling LLM (Local): ollama/ministral-3:8b"
# If missing: FilterAgent not being called
```

### PRIORITY 3: Test FilterAgent Manually

```python
# Inside container
from ai_safety_radar.agents.filter_agent import FilterAgent
from ai_safety_radar.utils.llm_client import LLMClient

filter_agent = FilterAgent(LLMClient())
result = await filter_agent.analyze(
    "Universal Jailbreak via Gradient-Based Suffix Optimization",
    "Abstract: We propose an automated method for generating adversarial suffixes..."
)
print(result.is_relevant)  # Should be True
```

### PRIORITY 4: Consider Simpler Architecture

Remove ingestion-level filtering, let agent_core handle all filtering:
- Pros: Guaranteed LLM filtering, simpler code
- Cons: More LLM calls, slower ingestion

---

## Environment

- **OS:** Podman containers on Linux
- **LLM:** ministral-3:8b on Jetson AGX Orin (192.168.1.37:11434)
- **Redis:** 7.x Alpine
- **Python:** 3.11
- **Framework:** LangGraph for agent workflows

---

## Known Good Papers for Testing

Test these papers manually to validate FilterAgent:

| Paper | Expected |
|-------|----------|
| "Universal Jailbreak via Gradient-Based Suffix Optimization" | ✅ ACCEPT |
| "Towards Provably Secure Generative AI: Reliable Consensus Sampling" | ✅ ACCEPT |
| "BatteryAgent: Battery Fault Diagnosis" | ❌ REJECT |

If FilterAgent rejects paper #1 or #2, the prompt is broken.

---

## Files to Investigate

| File | Purpose | Issue |
|------|---------|-------|
| `run_ingestion_service.py` | Ingestion filtering | May have old code running |
| `filter_agent.py` | LLM filter prompt | May be too conservative |
| `docker-compose.yml` | Service config | Check PYTHONPATH setting |

---

## Project Goal (Clarified)

**User's Intent:**
> "Track NEW AI Security research papers from ArXiv"
> Weekly digest of 10-20 relevant papers
> Like a RSS reader for AI Security research

**NOT:**
> Find "potential threats" in random AI papers
> Threat hunting in general ML papers

This is a **news aggregator**, not a **threat detector**.

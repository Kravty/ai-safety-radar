# Project State - January 4, 2026

## Executive Summary

**Project Goal:** AI Security research news aggregator  
**Current Status:** 🔴 NOT FUNCTIONAL - Zero ArXiv papers being processed  
**Completion:** ~60% (dashboard works, ingestion pipeline broken)

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

---

## What's Broken 🔴

### Critical Issue: Zero ArXiv Paper Ingestion

**Problem:**  
Ingestion service fetches 10 papers from ArXiv but rejects ALL with "not security research".

**Evidence:**
```
INFO:__main__:⏭  REJECTED (not security research): Towards Provably Secure Generative AI...
INFO:__main__:Ingestion cycle complete. Queued 0 papers.
```

**Impact:**  
Dashboard shows only 2 manually inserted test papers. Core project goal (track new AI security research) is NOT achieved.

**Suspected Root Causes:**
1. FilterAgent prompt too conservative (rejects papers with academic language)
2. Ingestion may not be calling FilterAgent LLM (using old code)
3. Code changes not deployed (container restart issue)
4. PYTHONPATH may not affect ingestion service correctly

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

## Technical Debt

1. **Unclear Filtering Logic**
   - Code changes made but not reflected in running containers
   - Logs show OLD rejection format, not new LLM reasoning
   - Container rebuild may be required

2. **Deployment Verification**
   - `podman-compose restart` may not reload volume-mounted code
   - Need explicit `podman-compose down && up` or rebuild

3. **ArXiv Query**
   - Current query may be too narrow
   - Only fetches 10 papers (configurable via ARXIV_MAX_RESULTS)

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

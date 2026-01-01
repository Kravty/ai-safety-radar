# Implementation Log: AI Safety Radar

## [2025-12-01 10:00] - project-initialization

**Decision:** Initialize project using `uv` for dependency management and standard src-layout.
**Rationale:** `uv` provides faster resolution and lockfile management than pip/poetry. Src-layout prevents import parity issues.
**Result:** ✅ Success
**Code Locations:** `pyproject.toml`, `src/ai_safety_radar/`

## [2025-12-05 14:00] - ingestion-architecture

**Decision:** Implement `ArXivIngester` using `feedparser` and `httpx`.
**Rationale:** RSS/Atom feeds are efficient for bulk metadata retrieval.
**Issues Encountered:** ArXiv HTTP 301 Redirects causing failures.
**Resolution:** Enforced HTTPS in URL construction.
**Result:** ✅ Success
**Code Locations:** `src/ai_safety_radar/ingestion/arxiv.py`

## [2025-12-10 11:30] - agent-orchestration

**Decision:** Use `LangGraph` for multi-agent state management.
**Rationale:** Need cyclic graph capability for Curator-Critic loops which DAGs cannot handle easily.
**Alternatives Considered:** AutoGen (too complex for this scope), native hardcoded loops (too brittle).
**Result:** ✅ Success
**Code Locations:** `src/ai_safety_radar/orchestration/ingestion_graph.py`

## [2025-12-15 09:00] - container-isolation

**Decision:** Implement strict network isolation with 3 docker networks (`public_io`, `internal_msg`, `internal_model`).
**Rationale:** Zero Trust architecture. The `agent_core` must be air-gapped to prevent prompt injection data exfiltration.
**Result:** ✅ Success
**Code Locations:** `docker-compose.yml`

## [2025-12-18 16:00] - forensic-logging

**Decision:** Implement `ForensicLogger` using `structlog` and SHA256 input hashing.
**Rationale:** Need immutable, structured audit trails for security reviews without exposing full sensitive prompts in cleartext logs.
**Result:** ✅ Success
**Code Locations:** `src/ai_safety_radar/utils/logging.py`

## [2025-12-20 13:00] - redis-streams

**Decision:** Use Redis Streams (`XADD`, `XREAD`) for inter-service communication.
**Rationale:** Supports consumer groups (scalability) and persistence (AOF enabled). Decouples Ingestion from Core.
**Code Locations:** `src/ai_safety_radar/utils/redis_client.py`

## [2025-12-28 10:00] - docker-compose-fix

**Decision:** Fix `ModuleNotFoundError: No module named 'distutils'` on host.
**Rationale:** Python 3.12+ removed distutils, breaking legacy `docker-compose`.
**Resolution:** Updated documentation to recommend `docker-compose` V2 or `python3-setuptools`.
**Result:** ✅ Success

## [2025-12-28 12:00] - ollama-port-isolation

**Decision:** Remove `ports: 11434:11434` from Ollama service in docker-compose.
**Rationale:** Host binding caused port conflicts and violated the "internal model network" security boundary.
**Result:** ✅ Success
**Code Locations:** `docker-compose.yml`

## [2025-12-28 13:30] - docker-build-fix

**Decision:** Update Dockerfile to properly install the `ai_safety_radar` package.
**Issues Encountered:** `ModuleNotFoundError: No module named 'ai_safety_radar'` inside containers.
**Resolution:** Changed `RUN uv sync --frozen --no-dev` to `RUN uv sync --frozen` (implies project install).
**Result:** ✅ Success
**Code Locations:** `Dockerfile`

## [2025-12-28 14:00] - setup-script

**Decision:** Create `scripts/setup_ollama.sh` using a temporary container.
**Rationale:** `agent_core` loop and `ollama` service have no internet. We need a way to populate the volume with models *before* runtime.
**Code Locations:** `scripts/setup_ollama.sh`

## [2025-12-30 15:00] - dashboard-architecture

**Decision:** Add `dashboard` service to `internal_msg_net` with port `8501` exposed.
**Rationale:** Dashboard needs read access to Redis but shouldn't expose Redis to the host directly. Validates data diode pattern.
**Result:** ✅ Success
**Code Locations:** `docker-compose.yml`

## [2025-12-30 15:30] - integration-testing

**Decision:** Use `fakeredis` for integration tests.
**Rationale:** Ensures CI compatibility without requiring a sidecar Redis container.
**Result:** ✅ Success
**Code Locations:** `tests/integration/test_pipeline.py`

## [2025-12-30 16:00] - sota-tracker

**Decision:** Implement SOTA Tracker tab in Dashboard reading `curator:latest_summary`.
**Rationale:** Visualizes the "High Level" output of the multi-agent system, satisfying MATS demo requirements.
**Code Locations:** `src/ai_safety_radar/dashboard/app.py`

## [2025-12-30 16:30] - readme-automation

**Decision:** Create `update_readme.py` and `run_automation.sh` based on Redis stats.
**Rationale:** Demonstrates "living documentation" capabilities of the agentic system.
**Code Locations:** `src/ai_safety_radar/scripts/update_readme.py`

## [2026-01-01 16:45] - git-initialization

**Decision:** Establish local git version control and living documentation (`IMPLEMENTATION_LOG.md`).
**Rationale:** Need valid version control for project tracking and potential handover.
**Result:** ✅ Success

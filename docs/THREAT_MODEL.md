# Threat Model - AI Safety Radar

## 1. Description
The AI Safety Radar is an automated red-teaming tool that ingests research papers and uses LLM agents to extract threat signatures. Security is critical to prevent the tool itself from becoming a vector for attacks (e.g. Prompt Injection leading to RCE).

## 2. Critical Assets
- **Host System**: The machine running the Docker containers.
- **Internal Network**: access to Redis/OLLAMA.
- **Data Integrity**: The `ThreatSignature` database.

## 3. Threat Scenarios & Mitigations

### A. Prompt Injection / Jailbreak via ArXiv Paper
**Risk**: A malicious paper contains a prompt injection payload designed to execute code or exfiltrate data when processed by the `ExtractionAgent` or `FilterAgent`.
**Impact**: High (RCE or Data Exfiltration).
**Mitigation**:
- **Agent Air-Gap**: The `agent_core` container has NO Internet access. Even if an injection succeeds in coercing the LLM to "fetch URL", the request will fail.
- **Container Hardening**: `agent_core` runs as non-root (`1000:1000`) with no capabilities (`cap_drop: ALL`). RCE is contained.
- **Forensic Logging**: All input prompts are hashed and logged to `audit.jsonl` for post-mortem analysis.

### B. Supply Chain Compromise (PyPI/Docker)
**Risk**: A dependency is compromised.
**Impact**: Critical.
**Mitigation**:
- **Strict Pinning**: `uv.lock` ensures reproducible builds.
- **Network Isolation**: Compromised agent code cannot call home (C2) due to the air-gap.

### C. Data Exfiltration via Side Channel
**Risk**: Exfiltrating data via DNS or subtle channels.
**Impact**: Medium.
**Mitigation**:
- **Internal Networks**: `agent_core` is on `internal_msg_net` (Redis only) and `internal_model_net` (Ollama only). Docker internal networks block outbound traffic, including DNS.

### D. Adversarial Paper Injection (Filter Bypass)
**Risk**: Attacker publishes paper with keywords designed to bypass filter.
**Example**:
```
Title: "Optimizing Neural Network Training" (benign-looking)
Abstract: "jailbreak adversarial prompt injection..." (keyword stuffing)
```
**Impact**: Low (paper gets accepted but no execution risk)
**Mitigation**:
- **Two-stage validation** - Regex + LLM both must agree
- **ML anchor requirement** - Keywords need ML context
- **Critic agent** - Validates extraction quality
- **Human review** - Dashboard allows manual rejection

### E. Filter Drift (Concept Drift)
**Risk**: AI Security field evolves, filter becomes outdated.
**Example**: New attack class "prompt smuggling" not in keyword list.
**Impact**: Medium (may miss relevant papers)
**Mitigation**:
- **Configurable patterns** - Update regex in `filter_logic.py`
- **LLM fallback** - Catches novel patterns
- **Monitoring** - Track rejection rate over time
- **User feedback** - Manual additions flag missing patterns

**Recommendation**: Review filter patterns quarterly, update based on field evolution.

## 4. Residual Risks
- **Ollama Vulnerabilities**: If the local Ollama instance is compromised via the internal network, it could affect the host. (Mitigation: Keep Ollama updated).
- **Redis DoS**: Malformed messages could crash the Redis consumer. (Mitigation: Future DLQ implementation).
- **Filter False Negatives**: Strict filtering may miss some relevant papers. (Mitigation: Manual review, user feedback loop).

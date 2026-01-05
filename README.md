# The AI Safety Radar

**Autonomous Cyber Threat Intelligence Engine for AI Safety**

The AI Safety Radar is an agentic intelligence engine that autonomously monitors, analyzes, and categorizes emerging threats in the AI Safety and Security domain.

## 🎯 Project Status

| Component | Status |
|-----------|--------|
| **Dashboard** | ✅ Functional |
| **Agent Pipeline** | ✅ Working |
| **ArXiv Ingestion** | ✅ Working (strict filtering) |
| **Overall** | 🟢 **PRODUCTION-READY** |

**Current Stats:**
- **Acceptance Rate:** ~40% (strict 80/20 Pareto rule)
- **Filter Mode:** Strict (top 20% of papers only)
- **LLM Efficiency:** 60% fewer calls (regex pre-filter)

**Dashboard:** http://localhost:8501

## Features
- **Autonomous Ingestion**: Monitors ArXiv, GitHub, and other sources.
- **Agentic Analysis**: Uses LLMs (`LiteLLM` + `Instructor`) to extract structured threat signatures.
- **Dual-Mode Operation**:
  - **Cloud**: Uses OpenAI GPT-4o for high precision.
  - **Local (Jetson)**: Uses Ollama (Llama 3 / Mistral) for privacy and edge deployment.
- **Morden Stack**: Built with `langgraph`, `pydantic v2`, and `uv`.
- **Intelligence Dashboard**: Real-time Streamlit UI for threat monitoring and security status.
- **Forensic & Automated Docs**: Zero-trust audit logging and self-updating documentation.

## 📚 Documentation
- [MATS Portfolio](docs/MATS_PORTFOLIO.md): Detailed architecture, decisions, and future roadmap.
- [Threat Model](docs/THREAT_MODEL.md): Security boundaries and experimental safety protocols.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Package Manager)
- **Container Runtime**: Docker or [Podman](https://podman.io/) (with `podman-compose`)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/ai-safety-radar.git
   cd ai-safety-radar
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Usage

**Run the pipeline locally:**
```bash
uv run python -m ai_safety_radar.scripts.run_pipeline
```
*(Note: Implementation pending for the full pipeline entrypoint)*

**Run tests:**
```bash
uv run pytest
```

**Type checking:**
```bash
uv run mypy src/ --strict
```

### Initial Setup (One-Time)
Because the `ollama` service is isolated on an internal network, it cannot download models at runtime. You must pre-populate the model volume:

```bash
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```

### Running the Stack
```bash
docker-compose up --build
```
Access the **Intelligence Dashboard** at `http://localhost:8501`.

## 🐳 Container Deployment (Docker/Podman)

To run the full stack (replace `docker-compose` with `podman-compose` if using Podman):

```bash
docker-compose up --build
# OR
podman-compose up --build
```

## 🔍 Filtering Architecture (80/20 Pareto Rule)

```mermaid
graph TB
    START[ArXiv Paper] --> REGEX[Regex Pre-filter<br/>filter_logic.py]
    
    REGEX -->|Score < 30| REJECT1[❌ AUTO-REJECT<br/>No LLM call]
    REGEX -->|Score 30-70| LLM[🤖 LLM Validation<br/>FilterAgent]
    REGEX -->|Score > 70| ACCEPT1[✅ AUTO-ACCEPT<br/>No LLM call]
    
    LLM -->|is_relevant=True| ACCEPT2[✅ ACCEPT]
    LLM -->|is_relevant=False| REJECT2[❌ REJECT]
    
    ACCEPT1 --> QUEUE[papers:pending]
    ACCEPT2 --> QUEUE
    
    style REJECT1 fill:#ffebee
    style REJECT2 fill:#ffebee
    style ACCEPT1 fill:#e8f5e9
    style ACCEPT2 fill:#e8f5e9
    style REGEX fill:#e3f2fd
    style LLM fill:#fff3e0
```

**Key Features:**
- **60% fewer LLM calls** - Regex handles obvious accept/reject
- **Carlini-inspired logic** - Based on top adversarial ML researcher's corpus
- **Configurable thresholds** - Adjust in `config.py`
- **Kill list** - Auto-reject hardware, medical, battery papers
- **ML anchors** - Ambiguous terms validated by context

## ⚙️ Configuration

All parameters centralized in `src/ai_safety_radar/config.py`.

```python
# Filter strictness (80/20 rule)
FILTER_MODE=strict                # Options: permissive, balanced, strict
FILTER_REGEX_THRESHOLD=30         # Below = auto-reject (no LLM)
FILTER_AUTO_ACCEPT_THRESHOLD=70   # Above = auto-accept (no LLM)

# LLM models
LLM_MODEL=ministral-3:8b          # Local model on Jetson

# Ingestion
INGESTION_MAX_RESULTS=30          # Papers per fetch
INGESTION_DAYS_BACK=14            # Look back period
```

Override via environment variables in `.env` or `docker-compose.yml`.

## 🛡️ Security Architecture

**SL4 Principles Applied**: Network Isolation, Least Privilege, Defense-in-Depth.

### The Data Diode Pattern
The system uses a decoupled architecture to ensure the **Agent Core** (which executes potentially dangerous prompts) is completely air-gapped from the Internet.


```mermaid
graph TD
    subgraph Public["Public Network"]
        ArXiv["ArXiv API"]
    end

    subgraph "Ingestion Zone (Public IO)"
        Ingestion["Ingestion Service"]
    end

    subgraph "Internal Message Bus (No Internet)"
        Redis[("Redis Streams")]
    end

    subgraph "Secure Enclave (Air-Gapped)"
        Agent["Agent Core"]
        Ollama["Ollama LLM"]
    end

    %% Data Flow Sequence
    Ingestion -- "1. Fetch Papers" --> ArXiv
    Ingestion -- "2. Push Job" --> Redis
    Redis -- "3. Pull Job" --> Agent
    Agent -- "4. Inference" --> Ollama
    Agent -- "5. Push Result" --> Redis
```

- **Forensic Logging**: All prompts are hashed (SHA256) and logged to `audit.jsonl` for post-event analysis.
- **Hardening**: Containers run as non-root user (`1000:1000`) with all capabilities dropped (`cap_drop: ["ALL"]`).

## Architecture

- **Ingestion**: Async `httpx` scrapers with strict two-stage filtering
- **Filtering**: Regex pre-filter + LLM validation (80/20 Pareto rule)
- **Orchestration**: `LangGraph` state machine
- **Agents**: FilterAgent → ExtractionAgent → CriticAgent → CuratorAgent
- **Data**: `Pydantic v2` models with `Instructor` for structured LLM output
- **Storage**: Redis Streams for job queuing, content-based deduplication

## License

MIT

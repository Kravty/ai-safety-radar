This is a comprehensive technical specification for **"The AI Safety Sentinel."** It is written to be handed directly to a Coding Agent or Senior Engineer for implementation.

It prioritizes **2025 Industry Standards**: composability, type safety (Pydantic), local-first capabilities (Edge AI), and data-centric design.

---

# **Project Specification: The AI Safety Sentinel**

### *Autonomous Cyber Threat Intelligence Engine for AI Safety*

## **1. Executive Summary**

**The AI Safety Sentinel** is an agentic intelligence engine that autonomously monitors, analyzes, and categorizes emerging threats in the AI Safety and Security domain. Unlike passive aggregators, it uses an **Agentic Workflow (LangGraph)** to "read" papers and code repositories, extracting structured threat signatures (Attack Vectors, Modalities, Severity) into a public, queryable database.

**Primary Goal:** To serve as the "gold standard" live dataset for AI Security researchers while demonstrating expert-level proficiency in **Applied AI Engineering**, **Agentic Orchestration**, and **MLOps**.

---

## **2. System Architecture**

The system follows an **Asynchronous Event-Driven Architecture**. It is designed to be **Model-Agnostic** (swappable between GPT-4o for precision and Llama-3-8B/Mistral on Jetson AGX for local privacy).

### **High-Level Data Flow**

1. **Ingestion Layer:** Async scrapers trigger on schedules (Cron/GitHub Actions).
2. **Orchestration Layer (The Brain):** A LangGraph state machine routes raw content to specific specialized agents.
3. **Reasoning Layer:** Agents use `LiteLLM` + `Instructor` to force structured extraction.
4. **Persistence Layer:** Validated data is appended to a **Hugging Face Dataset** (Parquet).
5. **Presentation Layer:** Streamlit Dashboard (HF Spaces) & Auto-updating READMEs.

---

## **3. Technology Stack (2025 Standards)**

| Component | Choice | Justification |
| --- | --- | --- |
| **Orchestration** | **LangGraph** | Enables cyclic, stateful agent workflows (e.g., "Human-in-the-loop" or "Self-Correction" loops) superior to linear chains. |
| **Model Gateway** | **LiteLLM** | Unified interface for 100+ providers. Allows seamless switching between OpenAI (Cloud) and Ollama/vLLM (Local Jetson). |
| **Structured Output** | **Instructor** | Patched over LiteLLM. Ensures rigorous Pydantic schema adherence, critical for local models that lack native function-calling. |
| **Concurrency** | **Python Asyncio** | Fully asynchronous scraping and processing pipeline to maximize throughput on I/O-bound tasks. Uses `httpx`. |
| **Data Validation** | **Pydantic V2** | Strict typing for all data flowing between agents. No "string guessing." |
| **Data Storage** | **HF Datasets** | Native Git-based versioning for data. Parquet format for high-performance columnar storage. |
| **Frontend** | **Streamlit** | Rapid development for the dashboard, hosted on Hugging Face Spaces. |
| **CI/CD** | **GitHub Actions** | Automated daily triggers for the ingestion pipeline. |

---

## **4. Functional Modules Description**

### **Module A: The Ingestion Swarm (Asyncio)**

* **Responsibility:** Fetch raw text metadata efficiently without blocking.
* **Sources:**
* **ArXiv API:** Filter for `cat:cs.CR`, `cat:cs.AI`, `cat:stat.ML`. Query keywords: *Adversarial, Jailbreak, Poisoning, Backdoor, Alignment*.
* **GitHub Trending:** Scrape `github.com/trending` with topic `ai-safety` or `security`.
* **Hugging Face Daily Papers:** API fetch.
* **Tech Blogs:** RSS parsing for Anthropic, OpenAI, DeepMind research blogs.


* **Architecture:** Implemented as a pool of async workers (`httpx`) that populate a `RawDocument` queue.

### **Module B: The Agentic Core (LangGraph)**

This is the "Brain" of the system, divided into two distinct workflows: the **Ingestion Pipeline** (Per-Document) and the **Editorial Loop** (Batch/Daily).

#### **1. The Ingestion Pipeline (Per-Document)**
*Handles the flow of raw data into structured intelligence.*

*   **`FilterAgent`:**
    *   **Role:** The Gatekeeper.
    *   **Input:** Raw Title & Abstract.
    *   **Logic:** Binary classification (Relevant/Irrelevant) with a confidence score. Filters out general AI news to focus strictly on Security/Safety.
    *   **Optimization:** Uses a cheap, fast model (e.g., Llama-3-8B-Quantized or gpt-4o-mini).

*   **`ExtractionAgent` (formerly AnalysisAgent):**
    *   **Role:** The Specialist.
    *   **Input:** Full Abstract & Metadata.
    *   **Logic:** Maps unstructured text to the strict `ThreatSignature` Pydantic schema.
    *   **Task:**
        *   Classifies Attack Vector (e.g., Jailbreak vs. Poisoning).
        *   Extracts "Affected Models" and "Severity".
        *   **Heuristic Check:** instead of executing code, it detects "Has Code" capability by analyzing metadata links (GitHub/GitLab) to determine `is_theoretical`.

#### **2. The Editorial Loop (Daily Batch Job)**
*Handles the synthesis of intelligence into human-readable insights for the dashboard.*

*   **`CuratorAgent`:**
    *   **Role:** The Editor-in-Chief.
    *   **Input:** Today's batch of new `ThreatSignatures` + Yesterday's "SOTA Summary."
    *   **Logic:** Synthesizes new data into the existing narrative.
    *   **Task:** Updates the "Current Threat Landscape" summary. Highlights emerging trends (e.g., "3 new vision jailbreaks detected this week").

*   **`CriticAgent`:**
    *   **Role:** The Quality Auditor.
    *   **Input:** The `CuratorAgent`'s draft update + The source batch data.
    *   **Logic:** Fact-checking and Hallucination Detection.
    *   **Task:** Verifies that claims in the summary are supported by the actual data rows.
    *   **Feedback Loop:** If issues are found, rejects the draft and sends it back to the Curator with specific correction instructions.



### **Module C: The Data Engineer (Persistence)**

* **Responsibility:** Git-based data management (Data-as-Code).
* **Logic:**
1. Receives validated `ThreatSignature` objects.
2. Pulls the latest dataset from Hugging Face Hub.
3. Performs deduplication (using Semantic ID based on Title/Authors).
4. Appends new rows.
5. Converts to **Parquet**.
6. Commits and Pushes back to the Hub via `huggingface_hub` Python API.



---

## **5. Data Schema (The Contract)**

We define strict Pydantic models to ensure the "Added Value" is high quality, structured data, not just text summaries.

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ThreatSignature(BaseModel):
    title: str
    url: str
    published_date: str
    
    # The Core Value-Add: AI Extraction
    relevance_score: float = Field(..., description="0.0 to 1.0 score of relevance to AI Safety")
    attack_type: Literal['Jailbreak', 'Prompt Injection', 'Data Poisoning', 'Backdoor', 'Model Extraction', 'Adversarial Example', 'Other']
    modality: List[Literal['Text', 'Vision', 'Audio', 'Multi-modal', 'Agentic']]
    affected_models: List[str] = Field(description="Specific models mentioned, e.g., 'GPT-4', 'Llama-2'")
    
    # "Expert" Metadata
    is_theoretical: bool = Field(description="True if paper only, False if code/PoC exists")
    severity: int = Field(description="1-5 scale based on reproducibility and impact")
    summary_tldr: str = Field(description="One sentence technical summary for experts")

```

---

## **6. Deliverables & User Experience**

### **1. The Live Database (Hugging Face Dataset)**

* **Format:** Parquet file hosted on HF Datasets.
* **Value:** Researchers can load it in one line:
```python
from datasets import load_dataset
dataset = load_dataset("your-username/ai-safety-sentinel")
# Instant access to structured attack data

```



### **2. The "Mission Control" Dashboard (Streamlit)**

* **Host:** Hugging Face Spaces (Dockerized).
* **Features:**
* **Threat Radar:** A heatmap showing active attack vectors this week (e.g., "Spike in Vision Jailbreaks").
* **Semantic Search:** Search for "Methods to bypass Llama-3 guardrails" (using vector embedding of the summaries).
* **Daily Brief:** A generated "Morning Report" section.



### **3. GitHub Presence (The "Living" Repo)**

* **Action:** A final step in the pipeline updates your `README.md` automatically.
* **Content:**
* "🚨 **Latest Critical Threats (Last 24h)**" table inserted directly into the README.
* Badges showing "X Threats Detected Today."



### **4. RSS Feed Generator**

* **Implementation:** A simple script generates an `atom.xml` file and commits it to GitHub Pages or the HF Space static directory. Allows researchers to subscribe via Feedly.

---

## **7. Infrastructure & Local/Cloud Hybrid Strategy**

**The "Hybrid" configuration is key to showcasing your pragmatism:**

1. **Development/Production (Cloud Mode):**
* **Env:** GitHub Actions Runner.
* **Model:** `LiteLLM` pointing to `gpt-4o-mini` (cheap, fast) or `claude-3-haiku`.
* **Why:** Reliability for the daily cron job.


2. **Edge Research (Local Mode - Jetson AGX):**
* **Env:** Docker container running on Jetson.
* **Model:** `LiteLLM` pointing to local `Ollama` endpoint (running `llama-3-8b-instruct` or `mistral`).
* **Why:** Demonstrates **Privacy-First Engineering**. You can ingest private/internal papers without sending data to OpenAI.



---

## **8. Step-by-Step Implementation Prompt for Coding Agent**

*(Copy this when you are ready to start coding)*

> "I need to initialize the repository for 'The AI Safety Sentinel.'
> **Phase 1 Goals:**
> 1. Set up a Python project with `uv` python package manager.
> 2. Create the `ThreatSignature` Pydantic schema using `instructor`.
> 3. implement a basic `IngestionService` for ArXiv using `asyncio` and `feedparser`.
> 4. Create a LangGraph workflow that takes a raw text, passes it to an LLM via `LiteLLM`, and attempts to extract the `ThreatSignature`.
> 
> 
> **Constraints:**
> * Use strict typing (mypy).
> * Prepare a `docker-compose.yml` that includes a service for the app and a service for a local Ollama instance (for Jetson compatibility).
> * No UI yet, just the backend pipeline."
> 
>
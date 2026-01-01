# CONTEXT
You are implementing Phase 1 of "The AI Safety Radar" - an autonomous cyber threat intelligence engine for AI Safety. This is a production-grade Python project showcasing expert-level AI engineering, agentic orchestration, and MLOps practices.

# YOUR TASK
Initialize the complete project foundation including:
1. Project structure with modern Python tooling using `uv` python package manager
2. Core Pydantic data models for threat signatures
3. Basic ingestion service skeleton for ArXiv
4. LangGraph workflow foundation
5. Configuration management system

# TECHNICAL REQUIREMENTS

## Technology Stack
- **Python**: 3.11+ with strict type hints
- **Package Manager**: `uv` (not pip)
- **Orchestration**: LangGraph for agentic workflows
- **Model Gateway**: LiteLLM (unified interface for OpenAI/Ollama)
- **Structured Output**: Instructor (Pydantic validation)
- **Concurrency**: asyncio for I/O-bound operations
- **Data Validation**: Pydantic V2 with strict mode
- **Data Storage**: Hugging Face Datasets (Parquet format)
- **Testing**: pytest with pytest-asyncio
- **Linting**: ruff (replaces black + flake8 + isort)
- **Type Checking**: mypy with strict mode

## Project Structure
Create this exact structure:
```
ai-safety-radar/
├── pyproject.toml              # Poetry configuration
├── README.md                   # Auto-updating dashboard
├── .env.example                # Environment template
├── .gitignore
├── docker-compose.yml          # Local + Jetson deployment
├── Dockerfile
├── src/
│   ├── ai_safety_radar/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── threat_signature.py  # Core schema
│   │   │   └── raw_document.py
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Abstract base ingester
│   │   │   ├── arxiv.py        # ArXiv scraper
│   │   │   └── github.py       # GitHub trending (stub)
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── filter_agent.py
│   │   │   ├── analysis_agent.py
│   │   │   └── code_review_agent.py
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   └── workflow.py     # LangGraph state machine
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   └── dataset_manager.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── llm_client.py   # LiteLLM + Instructor wrapper
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_ingestion.py
└── scripts/
    └── run_pipeline.py         # CLI entry point
```

## Code Quality Standards

### Type Safety
```
# REQUIRED: Every function must have complete type hints
from typing import List, Optional
from pathlib import Path

def process_documents(
    docs: List[RawDocument],
    output_path: Path,
    max_workers: int = 10
) -> tuple[int, List[str]]:
    """Process documents and return success count and errors.
    
    Args:
        docs: List of raw documents to process
        output_path: Directory for processed output
        max_workers: Max concurrent workers
        
    Returns:
        Tuple of (successful_count, error_messages)
        
    Raises:
        ValueError: If output_path doesn't exist
    """
    pass
```

### Documentation
- Use Google-style docstrings for ALL functions/classes
- Include Args, Returns, Raises sections
- Add usage examples for complex functions

### Error Handling
- Never use bare `except:` clauses
- Always specify exception types
- Use custom exceptions for domain errors:
```
class IngestionError(Exception):
    """Raised when document ingestion fails."""
    pass
```

### Async Best Practices
- All I/O operations must be async
- Use `asyncio.gather()` for concurrent tasks
- Include proper timeout handling with `asyncio.wait_for()`

## Specific Deliverables

### 1. pyproject.toml
Include these exact dependencies:
```
[tool.poetry.dependencies]
python = "^3.11"
langgraph = "^0.2"
litellm = "^1.45"
instructor = "^1.3"
pydantic = "^2.8"
aiohttp = "^3.9"
feedparser = "^6.0"
huggingface-hub = "^0.24"
datasets = "^2.20"
streamlit = "^1.37"
python-dotenv = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.23"
mypy = "^1.11"
ruff = "^0.5"
```

### 2. Core Data Model (src/ai_safety_radar/models/threat_signature.py)
Implement the exact schema from the specification:
```
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime

class ThreatSignature(BaseModel):
    """Structured representation of an AI security threat."""
    
    title: str = Field(..., min_length=5, max_length=500)
    url: str = Field(..., pattern=r'^https?://')
    published_date: datetime
    
    # AI-extracted intelligence
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    attack_type: Literal[
        'Jailbreak',
        'Prompt Injection', 
        'Data Poisoning',
        'Backdoor',
        'Model Extraction',
        'Adversarial Example',
        'Other'
    ]
    modality: List[Literal['Text', 'Vision', 'Audio', 'Multi-modal', 'Agentic']]
    affected_models: List[str] = Field(default_factory=list)
    
    # Expert metadata
    is_theoretical: bool
    severity: int = Field(..., ge=1, le=5)
    summary_tldr: str = Field(..., max_length=280)
    
    # Internal tracking
    source: str = Field(..., description="Ingestion source: arxiv, github, etc")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Universal Jailbreak for GPT-4",
                "url": "https://arxiv.org/abs/2024.xxxxx",
                "published_date": "2025-12-01T00:00:00Z",
                "relevance_score": 0.95,
                "attack_type": "Jailbreak",
                "modality": ["Text"],
                "affected_models": ["GPT-4", "GPT-4-Turbo"],
                "is_theoretical": False,
                "severity": 5,
                "summary_tldr": "Novel prefix-based jailbreak bypassing system prompts",
                "source": "arxiv"
            }
        }
```

### 3. Configuration Management (src/ai_safety_radar/config.py)
Use Pydantic Settings for environment-based config:
```
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # LLM Configuration
    llm_provider: Literal["openai", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    
    # Ingestion
    arxiv_max_results: int = 50
    github_trending_topics: list[str] = ["ai-safety", "security"]
    
    # Data Storage
    hf_dataset_name: str = "your-username/ai-safety-radar"
    hf_token: str | None = None
    
    # Processing
    max_concurrent_requests: int = 10
    request_timeout: int = 30

settings = Settings()
```

### 4. Async ArXiv Ingestion (src/ai_safety_radar/ingestion/arxiv.py)
Implement async scraping with proper error handling:
```
import asyncio
import aiohttp
import feedparser
from typing import AsyncIterator
from ..models.raw_document import RawDocument
from ..config import settings

class ArXivIngester:
    """Async scraper for ArXiv papers related to AI safety."""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    SAFETY_KEYWORDS = [
        "adversarial",
        "jailbreak", 
        "alignment",
        "poisoning",
        "backdoor",
        "robustness"
    ]
    
    async def fetch_recent(
        self,
        days_back: int = 7,
        max_results: int | None = None
    ) -> AsyncIterator[RawDocument]:
        """
        Fetch recent papers matching AI safety keywords.
        
        Args:
            days_back: Number of days to look back
            max_results: Max papers to return (None = unlimited)
            
        Yields:
            RawDocument instances for each relevant paper
            
        Raises:
            aiohttp.ClientError: If API request fails
        """
        # Implementation with proper async/await, error handling
        # Use aiohttp for requests, feedparser for parsing
        # Include rate limiting (1 request per 3 seconds per ArXiv policy)
        pass
```

### 5. LiteLLM + Instructor Wrapper (src/ai_safety_radar/utils/llm_client.py)
Create a unified client that works with both cloud and local models:
```
import instructor
from litellm import acompletion
from pydantic import BaseModel
from typing import TypeVar, Type
from ..config import settings

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """Wrapper around LiteLLM + Instructor for structured extraction."""
    
    def __init__(self):
        self.client = instructor.from_litellm(acompletion)
    
    async def extract(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1
    ) -> T:
        """
        Extract structured data from text using LLM.
        
        Args:
            prompt: User prompt text
            response_model: Pydantic model to extract
            system_prompt: Optional system instructions
            temperature: Sampling temperature
            
        Returns:
            Instance of response_model with extracted data
            
        Raises:
            instructor.exceptions.InstructorRetryException: If extraction fails
        """
        # Implementation using instructor's patching
        pass
```

### 6. Docker Configuration (docker-compose.yml)
Support both cloud and local (Jetson) deployment:
```
version: '3.8'

services:
  app:
    build: .
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - ollama
    command: python scripts/run_pipeline.py

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

## CONSTRAINTS
- NO placeholder comments like `# TODO: implement`
- NO print statements (use logging module)
- ALL async functions must have proper timeout handling
- MUST pass `mypy --strict` with zero errors
- Include comprehensive docstrings for every public function

## VALIDATION CHECKLIST
Before submitting, ensure:
- [ ] `poetry install` succeeds without errors
- [ ] `mypy src/ --strict` passes
- [ ] `ruff check src/` passes
- [ ] All test files have at least one test
- [ ] README.md includes setup instructions
- [ ] .env.example has all required keys documented

## OUTPUT FORMAT
Provide files in this order:
1. pyproject.toml
2. .gitignore
3. .env.example
4. src/ai_safety_radar/config.py
5. src/ai_safety_radar/models/threat_signature.py
6. src/ai_safety_radar/models/raw_document.py
7. src/ai_safety_radar/ingestion/base.py
8. src/ai_safety_radar/ingestion/arxiv.py
9. src/ai_safety_radar/utils/llm_client.py
10. docker-compose.yml
11. Dockerfile
12. README.md

For each file, use this format:
```
## File: path/to/file.py
\```python
[complete file contents]
\```
```

# ADDITIONAL CONTEXT
This project will be open-sourced on GitHub and hosted on Hugging Face Spaces. Code quality is critical as it serves as a portfolio showcase. Prioritize readability, maintainability, and adherence to 2025 Python best practices.
```
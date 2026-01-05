"""
Centralized configuration for AI Safety Radar.
All parameters in one place, overridable via environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, List

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === LLM Configuration ===
    llm_provider: Literal["openai", "ollama"] = Field(
        default="ollama",
        description="LLM provider: 'openai' or 'ollama'"
    )
    llm_model: str = Field(
        default="ministral-3:8b",
        description="Model for all agents (FilterAgent, ExtractionAgent, etc.)"
    )
    openai_api_key: str | None = Field(default=None)
    ollama_base_url: str = Field(
        default="http://192.168.1.37:11434",
        description="Ollama API endpoint (Jetson remote inference)"
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0 = deterministic)"
    )
    
    # === Ingestion Configuration ===
    arxiv_max_results: int = Field(
        default=30,
        description="Max papers to fetch per ingestion cycle"
    )
    arxiv_days_back: int = Field(
        default=14,
        description="Fetch papers from last N days"
    )
    ingestion_interval_seconds: int = Field(
        default=21600,  # 6 hours
        description="Auto-ingestion interval"
    )
    github_trending_topics: List[str] = Field(
        default=["ai-safety", "security"],
        description="GitHub topics to track"
    )
    
    # === Filter Configuration (80/20 Pareto Rule) ===
    filter_mode: Literal["permissive", "balanced", "strict"] = Field(
        default="strict",
        description="Filtering strictness: strict = top 20% only"
    )
    filter_min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to accept paper"
    )
    filter_regex_threshold: int = Field(
        default=30,
        description="Minimum regex score to proceed to LLM validation"
    )
    filter_auto_accept_threshold: int = Field(
        default=70,
        description="Regex score above which to auto-accept (skip LLM)"
    )
    filter_known_authors: List[str] = Field(
        default=[
            "Nicholas Carlini",
            "Dawn Song",
            "Ian Goodfellow",
            "Nicolas Papernot",
            "Florian Tramèr",
            "Aleksander Madry",
            "Percy Liang",
            "Dan Hendrycks"
        ],
        description="Auto-accept papers by known AI Security researchers"
    )
    
    # === Data Storage ===
    hf_dataset_name: str = Field(default="your-username/ai-safety-radar")
    hf_token: str | None = Field(default=None)
    
    # === Processing ===
    max_concurrent_requests: int = Field(default=10)
    request_timeout: int = Field(default=30)


settings = Settings()

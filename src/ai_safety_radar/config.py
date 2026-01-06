"""
Centralized configuration for AI Safety Radar.
All parameters in one place, overridable via environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, List
import yaml
from pathlib import Path

# Load YAML config if exists
def _load_yaml_config() -> dict:
    """Load config.yaml if it exists, else return empty dict."""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

_yaml = _load_yaml_config()

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === LLM Configuration ===
    # Separate models for filtering (fast/cheap) vs analysis (quality)
    llm_filter_model: str = Field(
        default=_yaml.get('llm', {}).get('filter_model', "gpt-5-nano"),
        description="Model for FilterAgent (fast, cheap)"
    )
    llm_analysis_model: str = Field(
        default=_yaml.get('llm', {}).get('analysis_model', "gpt-5-mini"),
        description="Model for ExtractionAgent, CriticAgent, CuratorAgent (quality)"
    )
    # Legacy single model field (for backward compatibility)
    llm_model: str = Field(
        default=_yaml.get('llm', {}).get('filter_model', "gpt-5-nano"),
        description="[DEPRECATED] Use llm_filter_model or llm_analysis_model"
    )
    openai_api_key: str | None = Field(default=None)
    ollama_base_url: str = Field(
        default=_yaml.get('llm', {}).get('base_url', "http://192.168.1.37:11434"),
        description="Ollama API endpoint (Jetson remote inference)"
    )
    llm_temperature: float = Field(
        default=_yaml.get('llm', {}).get('temperature', 0.0),
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0 = deterministic)"
    )
    
    # === Ingestion Configuration ===
    arxiv_max_results: int = Field(
        default=_yaml.get('ingestion', {}).get('max_results', 30),
        description="Max papers to fetch per ingestion cycle"
    )
    arxiv_days_back: int = Field(
        default=_yaml.get('ingestion', {}).get('days_back', 14),
        description="Fetch papers from last N days"
    )
    ingestion_interval_seconds: int = Field(
        default=_yaml.get('ingestion', {}).get('interval_seconds', 21600),
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

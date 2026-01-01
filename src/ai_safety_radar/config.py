from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, List

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore" # Allow extra fields in .env without error
    )
    
    # LLM Configuration
    llm_provider: Literal["openai", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    
    # Ingestion
    arxiv_max_results: int = 50
    github_trending_topics: List[str] = ["ai-safety", "security"]
    
    # Data Storage
    hf_dataset_name: str = "your-username/ai-safety-radar"
    hf_token: str | None = None
    
    # Processing
    max_concurrent_requests: int = 10
    request_timeout: int = 30

settings = Settings()

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

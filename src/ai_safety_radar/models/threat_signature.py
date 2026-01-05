from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Union
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
    severity: Union[int, Literal['Critical', 'High', 'Medium', 'Low', 'Info']] = Field(
        ..., 
        description="Severity level: 5=Critical, 4=High, 3=Medium, 2=Low, 1=Info"
    )
    
    @field_validator('severity', mode='before')
    @classmethod
    def convert_severity(cls, v):
        """Convert severity string to int if needed."""
        if isinstance(v, str):
            severity_map = {
                'critical': 5,
                'high': 4,
                'medium': 3,
                'low': 2,
                'info': 1
            }
            return severity_map.get(v.lower(), 1)
        if isinstance(v, int):
            if 1 <= v <= 5:
                return v
            return 1
        return 1
    summary_tldr: str = Field(..., max_length=280)
    
    # NEW FIELDS for Research Monitor
    summary_detailed: str = Field(
        ..., 
        description="150-250 word summary covering: methodology, key findings, implications"
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="3-5 bullet points of main results"
    )
    methodology_brief: str | None = Field(
        default=None,
        description="How the attack/defense was tested (datasets, models, metrics)"
    )
    code_repository: str | None = Field(
        default=None,
        description="GitHub/HuggingFace link if provided in paper"
    )
    arxiv_category: str = Field(
        default="cs.AI",
        description="Primary arXiv category"
    )
    citation_count: int | None = Field(
        default=0,
        description="Google Scholar citations (if available)"
    )
    
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

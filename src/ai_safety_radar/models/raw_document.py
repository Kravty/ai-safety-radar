from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class RawDocument(BaseModel):
    """Raw content ingested from external sources before processing."""
    
    id: str = Field(..., description="Unique identifier from source (e.g. arXiv ID)")
    title: str
    url: str
    content: str = Field(..., description="Full text, abstract, or relevant content")
    source: str = Field(..., description="Source name: arxiv, github, etc")
    published_date: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

from pydantic import BaseModel, Field
from typing import List
import logging
from ..utils.llm_client import LLMClient
from ..models.threat_signature import ThreatSignature as ThreatSig # Alias to avoid confusion if needed
from .curator_agent import DailyBriefing

logger = logging.getLogger(__name__)

class CritiqueResult(BaseModel):
    is_approved: bool = Field(..., description="True if the briefing is accurate and grounded")
    feedback: str = Field(..., description="Specific feedback if rejected, or approval comment")
    score: int = Field(..., ge=1, le=10, description="Quality score")

class CriticAgent:
    """Quality Auditor agent that validates briefings."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    async def critique(self, briefing: DailyBriefing, source_data: List[ThreatSig]) -> CritiqueResult:
        """Validate the briefing against source data."""
        
        source_summary = "\n".join([f"- {t.title}" for t in source_data])
        
        prompt = f"""
        Act as a strict Fact-Checker. Validate the following briefing against the source data.
        
        Source Data (Ground Truth):
        {source_summary}
        
        Draft Briefing:
        {briefing.headline}
        {briefing.summary_markdown}
        
        Check for:
        1. Hallucinations (mentioning papers not in source).
        2. Exaggerations (claiming Severity 5 when it's just 2).
        3. Missing critical info.
        
        If significant errors, reject (is_approved=False) and provide instructions.
        If minor nits or perfect, approve.
        """
        
        return await self.llm_client.extract(
            prompt=prompt,
            response_model=CritiqueResult,
            system_prompt="You are a pedantic fact-checker.",
            temperature=0.0
        )

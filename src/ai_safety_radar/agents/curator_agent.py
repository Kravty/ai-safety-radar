from pydantic import BaseModel, Field
from typing import List
import logging
from ..utils.llm_client import LLMClient
from ..models.threat_signature import ThreatSignature

logger = logging.getLogger(__name__)

class DailyBriefing(BaseModel):
    summary_markdown: str = Field(..., description="Markdown formatted summary of the threat landscape")
    highlighted_threat_ids: List[str] = Field(..., description="List of URL or IDs of most critical threats")
    headline: str = Field(..., description="Catchy headline for the daily update")

class CuratorAgent:
    """Editor-in-Chief agent that synthesizes daily briefings."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    async def draft_briefing(self, threats: List[ThreatSignature], previous_summary: str = "") -> DailyBriefing:
        """Synthesize a briefing from a list of threats."""
        if not threats:
             return DailyBriefing(
                 summary_markdown="No new significant threats detected today.",
                 highlighted_threat_ids=[],
                 headline="Quiet Day on the AI Front"
             )
             
        threat_text = "\n\n".join([f"- [{t.severity}/5] {t.title}: {t.summary_tldr} ({t.attack_type})" for t in threats])
        
        prompt = f"""
        You are the Curator for the AI Safety Radar.
        
        Yesterday's Context:
        {previous_summary}
        
        Today's New Threats:
        {threat_text}
        
        Task:
        1. Write a compelling daily briefing (markdown) summarizing the new threats.
        2. Highlight strict trends (e.g. "Surge in Vision Jailbreaks").
        3. Select the top 3 most critical threats to highlight.
        4. Integrate with previous context if relevant (e.g. "Continuing the trend from yesterday...").
        """
        
        return await self.llm_client.extract(
            prompt=prompt,
            response_model=DailyBriefing,
            system_prompt="You are an expert technical editor for AI Security.",
            temperature=0.2 # Slight creativity for narrative
        )
    
    async def revise_briefing(self, original_briefing: DailyBriefing, feedback: str) -> DailyBriefing:
        """Revise the briefing based on Critic feedback."""
        prompt = f"""
        Your previous draft was rejected by the Critic.
        
        Original Draft:
        {original_briefing.summary_markdown}
        
        Critic Feedback:
        {feedback}
        
        Please rewrite the briefing to address the feedback.
        """
        
        return await self.llm_client.extract(
            prompt=prompt,
            response_model=DailyBriefing,
            temperature=0.2
        )

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
        Generate an academic research digest (NOT a threat briefing):

        ## Format:

        ### 🔬 New Attack Research (X papers)
        - **[Paper Title]** by [Authors]: [1-sentence contribution] → [Affected systems]

        ### 🛡️ New Defense Research (X papers)
        - **[Paper Title]**: [Defense mechanism] → [Effectiveness: X% improvement]

        ### 📊 Research Trends
        [2-3 sentences on: common themes, gaps in literature, emerging directions]

        ### 🔔 Noteworthy Findings
        - [Highlight 1-2 most impactful discoveries this period]

        ## Example Output:
        ### 🔬 New Attack Research (2 papers)
        - **Universal Jailbreak via Gradient-Based Suffix Optimization**: Automated adversarial suffix generation achieving 90% success rate on GPT-4 → Affects all instruction-tuned LLMs
        - **Prompt Injection via Multi-Modal Embeddings**: Exploits vision-language models by hiding malicious instructions in images → Tested on GPT-4V, Claude 3

        ### 🛡️ New Defense Research (1 paper)
        - **Semantic Input Filters for LLM Security**: Embedding-based detection of malicious prompts → 85% detection, 5% false positives

        ### 📊 Research Trends
        Attack research currently outpaces defense development 2:1. Focus shifting from text-only to multi-modal attack vectors. No papers this period addressed deployment-time monitoring.

        Yesterday's Context:
        {previous_summary}
        
        Today's New Research Papers:
        {threat_text}
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

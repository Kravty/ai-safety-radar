from pydantic import BaseModel, Field
import logging
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FilterResult(BaseModel):
    is_relevant: bool = Field(..., description="True if document relates to AI Safety/Security/Red Teaming")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Brief explanation of the decision")

class FilterAgent:
    """Gatekeeper agent that filters raw documents for relevance."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    async def analyze(self, title: str, abstract: str) -> FilterResult:
        """Analyze if a document is relevant to AI Safety."""
        prompt = f"""
        Analyze the following research paper/article for relevance to AI Safety and Security.
        
        We are interested in: 
        - Jailbreaks, Prompt Injection, Adversarial Attacks
        - Model Robustness, Backdoors, Poisioning
        - AI Alignment, Control, Interpretability relevant to safety
        
        We are NOT interested in:
        - General AI capability improvements (e.g. "Better RAG")
        - Pure computer vision tasks without security focus
        - General software engineering
        
        Title: {title}
        Abstract: {abstract}
        """
        
        try:
            return await self.llm_client.extract(
                prompt=prompt,
                response_model=FilterResult,
                system_prompt="You are an expert AI Safety researcher acting as a filter.",
                temperature=0.0
            ) 
        except Exception as e:
            logger.error(f"FilterAgent error: {e}")
            # Fail safe: if error, mark as irrelevant to avoid noise, or relevant to be safe?
            # Let's mark as doubtful but log it. For now, re-raise or return default.
            # Returning a default 'False' to avoid breaking pipeline, but logging is crucial.
            return FilterResult(is_relevant=False, confidence_score=0.0, reasoning=f"Error: {e}")

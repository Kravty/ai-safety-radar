import logging
from typing import Optional
from pydantic import BaseModel, Field
from ..utils.llm_client import LLMClient
from ..models.threat_signature import ThreatSignature
from ..models.raw_document import RawDocument

logger = logging.getLogger(__name__)

class ExtractionResult(BaseModel):
    """Intermediate model for LLM extraction before injecting metadata."""
    title: str = Field(..., description="Exact title from the paper")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="How relevant to AI Security (0-1)")
    attack_type: str = Field(
        ..., 
        description="One of: Jailbreak, Prompt Injection, Data Poisoning, Backdoor, Model Extraction, Adversarial Example, Other"
    )
    modality: list[str] = Field(
        ..., 
        description="List from: Text, Vision, Audio, Multi-modal, Agentic"
    )
    affected_models: list[str] = Field(
        default_factory=list,
        description="List of AI models affected (e.g., GPT-4, Claude, Llama)"
    )
    is_theoretical: bool = Field(..., description="True if no empirical evaluation, False if tested")
    severity: str = Field(
        ..., 
        description="One of: Critical, High, Medium, Low, Info"
    )
    summary_tldr: str = Field(
        ..., 
        max_length=280,
        description="1 sentence core contribution (max 280 chars)"
    )
    summary_detailed: str = Field(
        ...,
        description="Full paragraph (150-250 words) covering: methodology, key findings, implications"
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="3-5 bullet points of main results"
    )
    methodology_brief: Optional[str] = Field(
        default=None,
        description="How the attack/defense was tested: datasets, models, metrics (50-100 words)"
    )
    code_repository: Optional[str] = Field(
        default=None,
        description="GitHub/HuggingFace URL if provided in paper"
    )

class ExtractionAgent:
    """Specialist agent that extracts structured research summaries using Instructor."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def process(self, doc: RawDocument) -> Optional[ThreatSignature]:
        """Convert a raw document into a structured ThreatSignature."""
        if not doc.content:
            logger.warning(f"Empty content for document {doc.id}")
            return None
            
        prompt = f"""
You are a research librarian for AI Security literature. Extract key information from this paper.

**Paper Details:**
Title: {doc.title}
Published: {doc.published_date}
Content:
{doc.content[:12000]}

**Instructions:**
- Extract ONLY what the authors actually discovered/claimed
- Do NOT invent or speculate
- For severity: Critical=exploited in wild, High=practical attack, Medium=requires expertise, Low=theoretical
- For attack_type: Choose the BEST match from the allowed values
- For modality: Select all that apply from the allowed values
- summary_detailed should be 150-250 words covering methodology, findings, and implications
- key_findings should be 3-5 concrete bullet points of results
"""
        
        try:
            # Use Instructor to get structured output with automatic validation
            extraction = await self.llm_client.extract(
                prompt=prompt,
                response_model=ExtractionResult,
                system_prompt="You are an expert AI Security research analyst. Be precise and factual.",
                temperature=0.0
            )
            
            # Convert ExtractionResult to ThreatSignature by adding metadata
            threat_sig = ThreatSignature(
                title=extraction.title,
                url=doc.url,
                published_date=doc.published_date,
                relevance_score=extraction.relevance_score,
                attack_type=extraction.attack_type,
                modality=extraction.modality,
                affected_models=extraction.affected_models,
                is_theoretical=extraction.is_theoretical,
                severity=extraction.severity,  # Pydantic validator will convert to int
                summary_tldr=extraction.summary_tldr,
                summary_detailed=extraction.summary_detailed,
                key_findings=extraction.key_findings,
                methodology_brief=extraction.methodology_brief,
                code_repository=extraction.code_repository,
                source=doc.source
            )
            
            logger.info(f"✅ Extracted: {threat_sig.title[:50]}... (severity={threat_sig.severity})")
            return threat_sig

        except Exception as e:
            logger.error(f"ExtractionAgent error for {doc.id}: {e}", exc_info=True)
            return None

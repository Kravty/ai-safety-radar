"""
FilterAgent: Two-stage filtering for AI Security research papers.

Stage 1: Fast regex-based pre-filter (deterministic, instant)
Stage 2: LLM validation (only for borderline cases)

Implements 80/20 Pareto rule - accept only top 20% most relevant papers.
"""
from pydantic import BaseModel, Field
import logging
from ..utils.llm_client import LLMClient
from ..config import settings
from .filter_logic import MLSecurityFilter

logger = logging.getLogger(__name__)


class FilterResult(BaseModel):
    """Filter decision with reasoning FIRST to encourage thoughtful analysis."""
    reasoning: str = Field(
        ..., 
        description="Step-by-step analysis: identify safety-relevant keywords, assess significance"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="How certain are you? 0.9+ = clearly relevant/irrelevant"
    )
    is_relevant: bool = Field(
        ..., 
        description="Final decision: True if paper contributes to AI Safety/Security knowledge"
    )


class FilterAgent:
    """
    Gatekeeper agent that filters raw documents for relevance.
    
    Two-stage filtering:
    1. Regex pre-filter (fast, deterministic) - rejects obvious non-matches
    2. LLM validation (slow, nuanced) - only for borderline cases
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.ml_filter = MLSecurityFilter()
        
    async def analyze(self, title: str, abstract: str) -> FilterResult:
        """
        Analyze if a document is relevant to AI Safety research.
        Uses two-stage filtering to minimize LLM calls while maintaining quality.
        """
        
        # STAGE 1: Regex-based pre-filter (instant, deterministic)
        regex_result = self.ml_filter.evaluate(title, abstract)
        
        # If score too low, reject immediately (no LLM call needed)
        if regex_result["score"] < settings.filter_regex_threshold:
            logger.info(f"📋 FilterAgent: '{title[:50]}...'")
            logger.info(f"  ├─ Pre-filter: REJECT (score={regex_result['score']})")
            logger.info(f"  └─ Reasons: {regex_result['reasons']}")
            
            return FilterResult(
                is_relevant=False,
                confidence_score=regex_result["confidence"],
                reasoning=f"Pre-filter rejected (score={regex_result['score']}): {'; '.join(regex_result['reasons'])}"
            )
        
        # If score very high, auto-accept (no LLM call needed)
        if regex_result["score"] >= settings.filter_auto_accept_threshold:
            logger.info(f"📋 FilterAgent: '{title[:50]}...'")
            logger.info(f"  ├─ Pre-filter: AUTO-ACCEPT (score={regex_result['score']})")
            logger.info(f"  └─ Reasons: {regex_result['reasons']}")
            
            return FilterResult(
                is_relevant=True,
                confidence_score=regex_result["confidence"],
                reasoning=f"Strong match (score={regex_result['score']}): {'; '.join(regex_result['reasons'])}"
            )
        
        # STAGE 2: LLM validation (only for borderline cases: score 30-70)
        prompt = f"""You are filtering papers for an AI Security research aggregator applying the 80/20 Pareto rule.

**Pre-filter analysis:** Score={regex_result['score']}, Reasons={regex_result['reasons']}

**Paper:**
Title: {title}
Abstract: {abstract[:500]}

**ULTRA-STRICT CRITERIA (Top 20% Only):**

✅ ACCEPT **ONLY** if paper demonstrates:
1. **Concrete attacks** - Jailbreaks, adversarial examples, prompt injection, model extraction
2. **Security defenses** - Adversarial training, input validation, robustness methods
3. **Empirical security research** - Red teaming results, attack success rates, vulnerability discovery

❌ AUTO-REJECT if:
1. **Pure theory** - "Mathematical foundations", "theoretical framework", "geometry of reasoning"
2. **Tangential mentions** - "Applications to AI safety" without concrete security analysis
3. **Domain research** - Medical, physics, biology papers that use ML but aren't about ML security
4. **Optimization papers** - Faster training, better accuracy WITHOUT security angle
5. **Interpretability** - Feature attribution, explainability UNLESS tied to attack detection

**CRITICAL TEST:**
- Would a red team researcher cite this paper in a security report?
- Does the paper show HOW to attack or defend AI systems?
- Are there empirical results (success rates, benchmarks, exploits)?

If NO to all 3 → **REJECT**.

**Your decision:** ACCEPT or REJECT with reasoning (50-150 words)."""

        try:
            llm_result = await self.llm_client.extract(
                prompt=prompt,
                response_model=FilterResult,
                system_prompt="You are a strict AI Security research curator. Apply Pareto 80/20 rule - only accept top-tier relevant papers.",
                temperature=0.0
            )
            
            logger.info(f"📋 FilterAgent: '{title[:50]}...'")
            logger.info(f"  ├─ Pre-filter: {regex_result['score']} points")
            logger.info(f"  ├─ LLM: {'ACCEPT' if llm_result.is_relevant else 'REJECT'}")
            logger.info(f"  └─ Reasoning: {llm_result.reasoning[:80]}...")
            
            return llm_result
            
        except Exception as e:
            logger.error(f"FilterAgent LLM error: {e}")
            # On LLM error, use regex result as fallback
            return FilterResult(
                reasoning=f"LLM error, using pre-filter (score={regex_result['score']}): {e}",
                confidence_score=regex_result["confidence"],
                is_relevant=regex_result["status"] == "ACCEPT"
            )


import pytest
from ai_safety_radar.agents.filter_agent import FilterAgent, FilterResult
from ai_safety_radar.utils.llm_client import LLMClient


class MockLLMClient:
    """Mock LLM client for FilterAgent testing."""
    
    async def extract(self, prompt, response_model, system_prompt=None, temperature=0.0):
        """Mock extract() to return FilterResult based on paper characteristics."""
        
        # Analyze prompt content to determine paper relevance
        prompt_lower = prompt.lower()
        
        # Obvious jailbreak/attack papers
        if "jailbreak" in prompt_lower or "adversarial suffix" in prompt_lower:
            return FilterResult(
                reasoning="Paper discusses adversarial attacks on LLMs (jailbreak). Clear AI Security relevance with attack methodology and success rates mentioned.",
                confidence_score=0.95,
                is_relevant=True
            )
        
        # Security/safety papers
        if "secure" in prompt_lower and "generative ai" in prompt_lower:
            return FilterResult(
                reasoning="Paper addresses security frameworks for generative AI systems. Directly relevant to AI Safety research.",
                confidence_score=0.92,
                is_relevant=True
            )
        
        # Robustness papers (implicit safety relevance)
        if "robustness" in prompt_lower and "adversarial training" in prompt_lower:
            return FilterResult(
                reasoning="Paper discusses improving model robustness against adversarial inputs. This is safety-relevant defensive research.",
                confidence_score=0.88,
                is_relevant=True
            )
        
        # Non-security domain-specific papers
        if "battery" in prompt_lower:
            return FilterResult(
                reasoning="Paper focuses on battery fault diagnosis in physics domain. No transferable AI Security insights despite using neural networks.",
                confidence_score=0.85,
                is_relevant=False
            )
        
        # Default uncertain case
        return FilterResult(
            reasoning="Unclear relevance without more context.",
            confidence_score=0.5,
            is_relevant=False
        )


@pytest.fixture
def filter_agent():
    """Create FilterAgent with mock LLM."""
    return FilterAgent(llm_client=MockLLMClient())


@pytest.mark.asyncio
class TestFilterAgent:
    
    async def test_accept_jailbreak_paper(self, filter_agent):
        """FilterAgent should ACCEPT obvious jailbreak papers."""
        result = await filter_agent.analyze(
            title="Universal Jailbreak via Gradient-Based Suffix Optimization",
            abstract="We propose an automated method for generating adversarial suffixes that cause LLMs to produce harmful outputs."
        )
        
        assert result.is_relevant == True, f"Should accept jailbreak paper. Reasoning: {result.reasoning}"
        assert result.confidence_score >= 0.7
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 20
        
        print(f"✅ Accepted jailbreak paper (confidence: {result.confidence_score:.2f})")
        print(f"   Reasoning: {result.reasoning[:100]}...")
    
    async def test_accept_security_paper(self, filter_agent):
        """FilterAgent should ACCEPT security-focused papers."""
        result = await filter_agent.analyze(
            title="Adversarial Attacks on Secure Generative AI Systems",
            abstract="We present adversarial attack methods against security defenses in generative AI systems, demonstrating vulnerabilities in current robustness mechanisms."
        )
        
        assert result.is_relevant == True, f"Should accept security paper. Reasoning: {result.reasoning}"
        assert result.confidence_score >= 0.7
        
        print(f"✅ Accepted security paper (confidence: {result.confidence_score:.2f})")
        print(f"   Reasoning: {result.reasoning[:100]}...")
    
    async def test_reject_non_security_paper(self, filter_agent):
        """FilterAgent should REJECT domain-specific papers without AI security angle."""
        result = await filter_agent.analyze(
            title="BatteryAgent: Physics-Informed Battery Fault Diagnosis",
            abstract="We develop a system for detecting battery failures using physics-informed neural networks."
        )
        
        assert result.is_relevant == False, f"Should reject battery paper. Reasoning: {result.reasoning}"
        assert result.confidence_score >= 0.6
        
        print(f"✅ Rejected non-security paper (confidence: {result.confidence_score:.2f})")
        print(f"   Reasoning: {result.reasoning[:100]}...")
    
    async def test_accept_robustness_paper(self, filter_agent):
        """FilterAgent should ACCEPT robustness papers (implicit safety relevance)."""
        result = await filter_agent.analyze(
            title="Improving LLM Robustness via Adversarial Training",
            abstract="We propose adversarial training methods to improve model robustness against edge cases and limitations."
        )
        
        # This is a KEY test - "robustness" is implicit safety keyword
        assert result.is_relevant == True, f"Should accept robustness paper. Reasoning: {result.reasoning}"
        assert result.confidence_score >= 0.7
        
        print(f"✅ Accepted robustness paper (confidence: {result.confidence_score:.2f})")
        print(f"   Reasoning: {result.reasoning[:100]}...")
    
    async def test_result_structure(self, filter_agent):
        """Verify FilterResult has correct structure."""
        result = await filter_agent.analyze(
            title="Test Paper",
            abstract="Test abstract."
        )
        
        # Verify all required fields present
        assert hasattr(result, 'reasoning')
        assert hasattr(result, 'confidence_score')
        assert hasattr(result, 'is_relevant')
        
        # Verify types
        assert isinstance(result.reasoning, str)
        assert isinstance(result.confidence_score, float)
        assert isinstance(result.is_relevant, bool)
        
        # Verify constraints
        assert 0.0 <= result.confidence_score <= 1.0
        
        print(f"✅ FilterResult structure validated")


# To run: pytest tests/agents/test_filter_agent.py -v -s

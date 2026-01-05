import pytest
from datetime import datetime
from ai_safety_radar.agents.extraction_agent import ExtractionAgent, ExtractionResult
from ai_safety_radar.models.threat_signature import ThreatSignature
from ai_safety_radar.models.raw_document import RawDocument

# Import fixture
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tests.fixtures.papers import load_fixture

class MockLLMClient:
    """Mock LLM client that returns ExtractionResult (not ThreatSignature)."""
    
    async def extract(self, prompt, response_model, system_prompt=None, temperature=0.0):
        """Mock extract() to return ExtractionResult Pydantic model."""
        
        # Inspect prompt to determine which paper is being processed
        if "Universal Jailbreak" in prompt or "GCG" in prompt:
            return ExtractionResult(
                title="Universal Jailbreak via Gradient-Based Suffix Optimization",
                relevance_score=0.98,
                attack_type="Jailbreak",
                modality=["Text"],
                affected_models=["Llama-2", "GPT-3.5", "GPT-4"],
                is_theoretical=False,
                severity="Critical",  # String, will be converted to 5 by validator
                summary_tldr="GCG generates adversarial suffixes achieving 99% jailbreak success rate.",
                summary_detailed="The paper introduces Greedy Coordinate Gradient (GCG), an automated method for generating adversarial suffixes that cause aligned LLMs to produce harmful outputs. The method achieves 99% attack success rate on multiple models and demonstrates transferability across different model families. This represents a significant threat to LLM safety measures.",
                key_findings=[
                    "99% attack success rate on Llama-2 and GPT-3.5",
                    "Attacks transfer across model families",
                    "Automated gradient-based optimization"
                ],
                methodology_brief="Gradient-based optimization over discrete token space. Evaluated on harmful behavior dataset.",
                code_repository="https://github.com/llm-attacks/llm-attacks"
            )
        
        elif "Adversarial Training" in prompt or "Certifying Robustness" in prompt:
            return ExtractionResult(
                title="Certifying Robustness via Adversarial Training",
                relevance_score=0.85,
                attack_type="Adversarial Example",
                modality=["Text"],
                affected_models=["Classifiers"],
                is_theoretical=True,
                severity="Medium",  # String, will be converted to 3
                summary_tldr="New adversarial training method improving certified robustness by 5%.",
                summary_detailed="The paper proposes an adversarial training framework that provides certified robustness guarantees against L-infinity bounded attacks. The method combines randomized smoothing with adversarial training to achieve state-of-the-art certified accuracy improvements of 5% on standard benchmarks.",
                key_findings=[
                    "5% improvement in certified accuracy",
                    "Provable robustness guarantees",
                    "Scalable to large models"
                ],
                methodology_brief="Randomized smoothing + adversarial training. Evaluated on CIFAR-10 and ImageNet.",
                code_repository=None
            )
        
        else:
            # Default/fallback
            return None 

@pytest.fixture
def extraction_agent():
    return ExtractionAgent(llm_client=MockLLMClient())

@pytest.mark.asyncio
class TestExtractionAgent:
    
    async def test_jailbreak_paper_extraction(self, extraction_agent):
        """Test extraction of jailbreak research paper."""
        paper_data = load_fixture("gcg_jailbreak.json")
        doc = RawDocument(**paper_data)
        
        result = await extraction_agent.process(doc)
        
        # Verify extraction worked
        assert result is not None
        assert isinstance(result, ThreatSignature)
        
        # Check attack type
        assert result.attack_type == "Jailbreak"
        
        # Critical jailbreak should be severity 4-5
        assert result.severity >= 4, f"Expected high severity, got {result.severity}"
        
        # Should have meaningful content
        assert "GCG" in result.summary_tldr or "jailbreak" in result.summary_tldr.lower()
        assert len(result.summary_detailed) > 50
        
        # Should have key findings
        assert len(result.key_findings) > 0
        
        print(f"✅ Jailbreak extraction test passed")
        print(f"   Attack Type: {result.attack_type}")
        print(f"   Severity: {result.severity}")
        print(f"   Summary: {result.summary_tldr[:80]}...")
    
    async def test_defense_paper_extraction(self, extraction_agent):
        """Test extraction of defense/robustness research paper."""
        paper_data = load_fixture("adversarial_training_defense.json")
        doc = RawDocument(**paper_data)
        
        result = await extraction_agent.process(doc)
        
        assert result is not None
        assert isinstance(result, ThreatSignature)
        
        # Defense research should have moderate severity (not an active threat)
        assert result.severity <= 4, f"Defense paper should have moderate severity, got {result.severity}"
        
        # Should have description
        assert len(result.summary_detailed) > 30
        
        print(f"✅ Defense paper extraction test passed")
        print(f"   Attack Type: {result.attack_type}")
        print(f"   Severity: {result.severity}")
    
    async def test_severity_string_to_int_conversion(self, extraction_agent):
        """Test that severity string→int conversion works via Pydantic validator."""
        paper_data = load_fixture("gcg_jailbreak.json")
        doc = RawDocument(**paper_data)
        
        result = await extraction_agent.process(doc)
        
        # Verify severity is an integer (not string)
        assert isinstance(result.severity, int)
        assert 1 <= result.severity <= 5
        
        # Mock returns "Critical" string, should be converted to 5
        assert result.severity == 5
        
        print(f"✅ Severity conversion test passed: 'Critical' → {result.severity}")

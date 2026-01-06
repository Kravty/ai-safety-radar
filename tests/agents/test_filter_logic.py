"""
Tests for ML-Security paper filtering logic.
Validates regex-based pre-filter catches correct patterns.
"""
import pytest
from ai_safety_radar.agents.filter_logic import MLSecurityFilter


class TestMLSecurityFilter:
    """Test regex-based filtering logic."""
    
    def setup_method(self):
        self.filter = MLSecurityFilter()
    
    def test_strong_aml_signal_accepts(self):
        """Papers with strong AML signals should score high."""
        result = self.filter.evaluate(
            "Universal Jailbreak via Gradient-Based Suffix Optimization",
            "We propose adversarial attacks on aligned language models using gradient optimization."
        )
        assert result["status"] == "ACCEPT"
        assert result["score"] >= 50
        assert "STRONG_AML" in str(result["reasons"])
        print(f"✅ Jailbreak paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_kill_list_rejects_hardware(self):
        """Hardware security without ML context should be rejected."""
        result = self.filter.evaluate(
            "Detecting Hardware Trojans in FPGA Circuits",
            "We analyze power consumption patterns in integrated circuits using differential power analysis."
        )
        assert result["status"] == "REJECT"
        assert "KILL_LIST" in str(result["reasons"])
        print(f"✅ Hardware paper rejected: score={result['score']}, reasons={result['reasons']}")
    
    def test_battery_paper_rejected(self):
        """BatteryAgent should be rejected (domain-specific, no AI security)."""
        result = self.filter.evaluate(
            "BatteryAgent: Physics-Informed Battery Fault Diagnosis",
            "We develop a system for detecting battery failures using physics-informed neural networks."
        )
        # Battery + fault diagnosis triggers kill list
        assert result["status"] == "REJECT" or result["score"] < 50
        print(f"✅ Battery paper: score={result['score']}, status={result['status']}")
    
    def test_geometry_math_paper_rejected(self):
        """Pure mathematical reasoning paper without security angle should be rejected."""
        result = self.filter.evaluate(
            "Geometry of Reason: Spectral Signatures of Valid Mathematical Reasoning",
            "We present a training-free method to analyze mathematical reasoning validity using spectral analysis of transformer attention patterns."
        )
        # No strong AML signals, no safety terms
        assert result["score"] < 50, f"Expected low score, got {result['score']}"
        print(f"✅ Math paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_ambiguous_with_ml_anchor_accepts(self):
        """Backdoor + neural network context should validate."""
        result = self.filter.evaluate(
            "Backdoor Attacks on Federated Learning",
            "We poison training datasets to inject backdoors into neural networks during federated learning."
        )
        assert result["status"] == "ACCEPT"
        assert "VALIDATED_AMBIGUOUS" in str(result["reasons"]) or "STRONG_AML" in str(result["reasons"])
        print(f"✅ Backdoor paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_genai_boost(self):
        """Papers mentioning GPT/LLM should get boosted."""
        result = self.filter.evaluate(
            "Red Teaming GPT-4 with Automated Jailbreaks",
            "We test ChatGPT's safety guardrails using adversarial prompts and automated red teaming."
        )
        assert result["status"] == "ACCEPT"
        assert "GENAI_BOOST" in str(result["reasons"])
        assert result["score"] >= 60  # Should get strong signal + GenAI boost
        print(f"✅ GPT red team paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_safety_alignment_accepts(self):
        """AI safety/alignment papers should be accepted."""
        result = self.filter.evaluate(
            "Measuring AI Alignment: Behavioral Evaluation Methods",
            "We propose benchmarks for evaluating AI alignment and safety properties of large language models."
        )
        assert result["status"] == "ACCEPT"
        assert "SAFETY_TERMS" in str(result["reasons"]) or "STRONG_AML" in str(result["reasons"])
        print(f"✅ Alignment paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_pure_optimization_rejected(self):
        """Pure ML optimization without safety angle should be rejected."""
        result = self.filter.evaluate(
            "Faster Transformer Training via Gradient Checkpointing",
            "We propose a method to reduce memory usage during transformer training by 50%."
        )
        # No safety signals, just optimization
        assert result["score"] < 50
        print(f"✅ Optimization paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_medical_domain_rejected(self):
        """Medical domain AI without security angle should be rejected."""
        result = self.filter.evaluate(
            "Deep Learning for Cancer Detection in Radiology Images",
            "We train a neural network to detect tumors in medical images with 95% accuracy."
        )
        assert result["status"] == "REJECT" or result["score"] < 50
        print(f"✅ Medical paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_robustness_with_adversarial_accepts(self):
        """Adversarial robustness research should be accepted."""
        result = self.filter.evaluate(
            "Improving LLM Robustness via Adversarial Training",
            "We propose adversarial training methods to improve model robustness against adversarial perturbations."
        )
        assert result["status"] == "ACCEPT"
        assert result["score"] >= 50
        print(f"✅ Adversarial robustness paper: score={result['score']}, reasons={result['reasons']}")
    
    def test_unicode_handling(self):
        """Filter should handle non-ASCII characters."""
        result = self.filter.evaluate(
            "Universal Jailbreak via 对抗 Suffixes",
            "We propose adversarial attacks on LLMs using émojis 🚀 and unicode characters."
        )
        assert result["score"] > 0
        print(f"✅ Unicode paper: score={result['score']}")
    
    def test_very_short_abstract(self):
        """Filter should handle short abstracts."""
        result = self.filter.evaluate(
            "Adversarial Attack",
            "Jailbreak study"  # Only 2 words
        )
        # Should still score based on keywords
        assert result["score"] > 0
        print(f"✅ Short abstract: score={result['score']}")
    
    def test_very_long_text(self):
        """Filter should handle very long texts."""
        long_abstract = "adversarial attack " * 500  # Very long
        result = self.filter.evaluate(
            "Large Scale Adversarial Study",
            long_abstract
        )
        assert result["score"] > 0
        print(f"✅ Long text: score={result['score']}")
    
    def test_case_insensitive_matching(self):
        """Keywords should match case-insensitively."""
        result1 = self.filter.evaluate(
            "ADVERSARIAL ATTACK",
            "JAILBREAK STUDY"
        )
        result2 = self.filter.evaluate(
            "adversarial attack",
            "jailbreak study"
        )
        # Both should have similar high scores (>= 50)
        assert result1["score"] >= 50
        assert result2["score"] >= 50
        print(f"✅ Case insensitive: uppercase={result1['score']}, lowercase={result2['score']}")


# Run: pytest tests/agents/test_filter_logic.py -v -s

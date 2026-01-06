"""Test agent error handling."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from ai_safety_radar.agents.filter_agent import FilterAgent, FilterResult
from ai_safety_radar.agents.extraction_agent import ExtractionAgent
from ai_safety_radar.utils.llm_client import LLMClient


class TestFilterAgentErrors:
    
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock(spec=LLMClient)
        llm.extract = AsyncMock()
        return llm
    
    @pytest.fixture
    def agent(self, mock_llm):
        return FilterAgent(mock_llm)
    
    @pytest.mark.asyncio
    async def test_empty_title_graceful(self, agent):
        """Empty title should not crash."""
        result = await agent.analyze("", "Some abstract text")
        assert result.is_relevant == False
    
    @pytest.mark.asyncio
    async def test_empty_abstract_graceful(self, agent):
        """Empty abstract should not crash."""
        result = await agent.analyze("Some title", "")
        assert result.is_relevant == False
    
    @pytest.mark.asyncio
    async def test_both_empty_graceful(self, agent):
        """Both empty should not crash."""
        result = await agent.analyze("", "")
        assert result.is_relevant == False
    
    @pytest.mark.asyncio
    async def test_llm_error_handling(self, agent, mock_llm):
        """LLM errors should be handled gracefully."""
        mock_llm.extract.side_effect = Exception("LLM API error")
        
        # Use paper with moderate score to trigger LLM call
        result = await agent.analyze(
            "Adversarial robustness study", 
            "We investigate adversarial examples in machine learning models"
        )
        # Should still return a result (fallback to regex)
        assert result is not None
        assert isinstance(result.reasoning, str)

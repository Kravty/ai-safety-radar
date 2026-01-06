"""Test configuration."""
import pytest
import os
from ai_safety_radar.config import Settings


class TestConfigValidation:
    
    def test_default_config_loads(self):
        """Config should load without errors."""
        config = Settings()
        assert config.llm_model is not None
        assert config.filter_mode in ["permissive", "balanced", "strict"]
        assert config.arxiv_max_results > 0
        assert config.arxiv_days_back > 0
    
    def test_yaml_config_override(self):
        """YAML config values should be loaded."""
        config = Settings()
        # These should come from config.yaml
        assert config.llm_model == "ministral-3:8b"
        assert config.arxiv_max_results == 30
        assert config.arxiv_days_back == 14
    
    def test_env_var_override(self, monkeypatch):
        """Environment variables should override YAML."""
        monkeypatch.setenv("LLM_MODEL", "test-model")
        monkeypatch.setenv("ARXIV_MAX_RESULTS", "100")
        
        config = Settings()
        assert config.llm_model == "test-model"
        assert config.arxiv_max_results == 100
    
    def test_temperature_bounds(self, monkeypatch):
        """Temperature should be bounded between 0 and 2."""
        config = Settings()
        assert 0.0 <= config.llm_temperature <= 2.0
    
    def test_filter_mode_enum(self, monkeypatch):
        """Filter mode should only accept valid values."""
        # Valid values should work
        for mode in ["permissive", "balanced", "strict"]:
            monkeypatch.setenv("FILTER_MODE", mode)
            config = Settings()
            assert config.filter_mode == mode
    
    def test_confidence_threshold_bounds(self):
        """Confidence threshold should be between 0 and 1."""
        config = Settings()
        assert 0.0 <= config.filter_min_confidence <= 1.0
    
    def test_known_authors_list(self):
        """Known authors should be a non-empty list."""
        config = Settings()
        assert isinstance(config.filter_known_authors, list)
        assert len(config.filter_known_authors) > 0
        assert "Nicholas Carlini" in config.filter_known_authors
    
    def test_ollama_base_url_loaded(self):
        """Ollama base URL should be loaded from YAML."""
        config = Settings()
        # Should be loaded from config.yaml
        assert config.ollama_base_url is not None
        assert "http" in config.ollama_base_url
    
    def test_ingestion_interval_positive(self):
        """Ingestion interval should be positive."""
        config = Settings()
        assert config.ingestion_interval_seconds > 0

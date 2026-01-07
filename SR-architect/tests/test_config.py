
import pytest
import os
from unittest import mock
from core.config import Settings

def test_settings_defaults():
    """Test that default values are set correctly."""
    settings = Settings()
    assert settings.LLM_PROVIDER == "openrouter"
    assert settings.SCORE_THRESHOLD == 0.8
    assert settings.MAX_ITERATIONS == 3
    assert settings.WORKERS == 1

def test_settings_env_override():
    """Test that environment variables override defaults."""
    with mock.patch.dict(os.environ, {"MAX_ITERATIONS": "10", "LLM_PROVIDER": "ollama"}):
        # We need to re-instantiate Settings to pick up env vars
        settings = Settings()
        assert settings.MAX_ITERATIONS == 10
        assert settings.LLM_PROVIDER == "ollama"

def test_settings_types():
    """Test that types are coerced correctly."""
    with mock.patch.dict(os.environ, {"SCORE_THRESHOLD": "0.95"}):
        settings = Settings()
        assert settings.SCORE_THRESHOLD == 0.95
        assert isinstance(settings.SCORE_THRESHOLD, float)

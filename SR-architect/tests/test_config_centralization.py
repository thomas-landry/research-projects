"""
Tests for config centralization - ensures no os.getenv() outside config.py.

This test suite enforces COMPLETE centralization of all configuration.
Zero tolerance for scattered config.

User Requirements:
- All os.getenv() calls must be in config.py
- LLM selection centralized (default: Gemini on OpenRouter)
- API failure logging with specific error messages
- TDD adherence throughout
"""
import pytest
from pathlib import Path
from core.config import settings


class TestConfigCentralization:
    """Verify all config is centralized in config.py."""
    
    def test_no_os_getenv_in_core_modules(self):
        """Verify no os.getenv() calls in core/ modules (except config.py)."""
        core_dir = Path("core")
        violations = []
        
        for py_file in core_dir.glob("*.py"):
            if py_file.name == "config.py":
                continue
            
            content = py_file.read_text()
            if "os.getenv" in content:
                violations.append(str(py_file))
        
        assert not violations, f"Found os.getenv() in core/: {violations}"
    
    def test_no_os_getenv_in_agents(self):
        """Verify no os.getenv() calls in agents/."""
        agents_dir = Path("agents")
        violations = []
        
        for py_file in agents_dir.glob("*.py"):
            content = py_file.read_text()
            if "os.getenv" in content:
                violations.append(str(py_file))
        
        assert not violations, f"Found os.getenv() in agents/: {violations}"
    
    def test_config_has_all_api_keys(self):
        """Verify config.py has all required API keys."""
        # API keys
        assert hasattr(settings, 'OPENROUTER_API_KEY'), "Missing OPENROUTER_API_KEY"
        assert hasattr(settings, 'OPENAI_API_KEY'), "Missing OPENAI_API_KEY"
        assert hasattr(settings, 'NCBI_EMAIL'), "Missing NCBI_EMAIL"
        assert hasattr(settings, 'NCBI_API_KEY'), "Missing NCBI_API_KEY"
    
    def test_config_has_all_model_settings(self):
        """Verify config.py has all required model settings."""
        # Model names
        assert hasattr(settings, 'OPENROUTER_MODEL'), "Missing OPENROUTER_MODEL"
        assert hasattr(settings, 'OLLAMA_MODEL'), "Missing OLLAMA_MODEL"
        assert hasattr(settings, 'FALLBACK_MODEL'), "Missing FALLBACK_MODEL"
        assert hasattr(settings, 'TWO_PASS_LOCAL_MODEL'), "Missing TWO_PASS_LOCAL_MODEL"
        assert hasattr(settings, 'TWO_PASS_CLOUD_MODEL'), "Missing TWO_PASS_CLOUD_MODEL"
    
    def test_config_has_timeout_settings(self):
        """Verify config.py has all timeout/retry settings."""
        assert hasattr(settings, 'OLLAMA_HEALTH_CHECK_TIMEOUT'), "Missing OLLAMA_HEALTH_CHECK_TIMEOUT"
        assert hasattr(settings, 'PROCESS_KILL_GRACE_PERIOD'), "Missing PROCESS_KILL_GRACE_PERIOD"
        assert hasattr(settings, 'OLLAMA_RESTART_POLL_INTERVAL'), "Missing OLLAMA_RESTART_POLL_INTERVAL"
        assert hasattr(settings, 'OLLAMA_RESTART_MAX_ATTEMPTS'), "Missing OLLAMA_RESTART_MAX_ATTEMPTS"
    
    def test_default_llm_is_gemini_on_openrouter(self):
        """Verify default LLM is Gemini on OpenRouter (low cost)."""
        # User requirement: Default to Gemini on OpenRouter for low costs
        assert settings.LLM_PROVIDER == "openrouter", \
            f"Default provider should be 'openrouter', got '{settings.LLM_PROVIDER}'"
        
        # Default model should be Gemini (low cost)
        default_model = settings.OPENROUTER_MODEL
        assert "gemini" in default_model.lower(), \
            f"Default model should be Gemini for low costs, got '{default_model}'"
    
    def test_hybrid_mode_default_setting_exists(self):
        """Verify hybrid mode default is configurable."""
        assert hasattr(settings, 'HYBRID_MODE_DEFAULT'), "Missing HYBRID_MODE_DEFAULT"
        assert isinstance(settings.HYBRID_MODE_DEFAULT, bool), \
            "HYBRID_MODE_DEFAULT should be boolean"
    
    def test_no_custom_client_creation(self):
        """Verify no custom client creation outside utils.py."""
        violations = []
        
        for py_file in Path(".").rglob("*.py"):
            # Skip utils.py and test files
            if "utils.py" in str(py_file) or "test_" in py_file.name:
                continue
            
            # Skip __pycache__ and .git
            if "__pycache__" in str(py_file) or ".git" in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                # Check for direct instructor.patch or OpenAI() usage
                if "instructor.patch" in content or "= OpenAI(" in content:
                    violations.append(str(py_file))
            except Exception:
                pass  # Skip files that can't be read
        
        assert not violations, \
            f"Found custom client creation (should use utils.get_llm_client): {violations}"


class TestAPIFailureLogging:
    """Verify API failures are logged with specific error messages."""
    
    def test_client_has_connection_error_logging(self):
        """Verify client.py logs connection errors specifically."""
        client_file = Path("core/client.py")
        content = client_file.read_text()
        
        # Should have specific exception types
        assert "requests.Timeout" in content or "Timeout" in content, \
            "client.py should catch Timeout exceptions specifically"
        assert "requests.ConnectionError" in content or "ConnectionError" in content, \
            "client.py should catch ConnectionError exceptions specifically"
        
        # Should have logging for failures
        assert "logger" in content, "client.py should use logger for error reporting"
    
    def test_service_has_vectorization_error_logging(self):
        """Verify service.py logs vectorization failures."""
        service_file = Path("core/service.py")
        content = service_file.read_text()
        
        # Should log vectorization errors
        assert "logger.error" in content or "logger.warning" in content, \
            "service.py should log errors"


class TestConfigDocumentation:
    """Verify config.py has robust documentation."""
    
    def test_config_has_docstring(self):
        """Verify config.py has comprehensive docstring."""
        config_file = Path("core/config.py")
        content = config_file.read_text()
        
        # Should have class docstring
        assert '"""' in content or "'''" in content, \
            "config.py Settings class should have docstring"
        
        # Should mention centralization
        assert "central" in content.lower() or "configuration" in content.lower(), \
            "config.py should document centralization approach"
    
    def test_config_has_field_descriptions(self):
        """Verify config fields have descriptions."""
        config_file = Path("core/config.py")
        content = config_file.read_text()
        
        # Should use Field with description
        assert "Field(" in content, "Config should use pydantic Field with descriptions"
        assert "description=" in content or "env=" in content, \
            "Fields should have descriptions or env variable names"

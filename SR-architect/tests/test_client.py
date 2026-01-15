
import pytest
from unittest.mock import patch, MagicMock
from core.client import LLMClientFactory, OllamaHealthCheck
# OllamaHealthCheck is aliased to OllamaServiceManager in client.py
# which is imported from platform_utils.

@patch("core.platform_utils.requests.get")
def test_ollama_health_check_available(mock_get):
    mock_get.return_value.status_code = 200
    assert OllamaHealthCheck.is_available("http://localhost:11434") is True

@patch("core.platform_utils.requests.get")
def test_ollama_health_check_timeout(mock_get):
    import requests
    mock_get.side_effect = requests.Timeout("Timed out")
    assert OllamaHealthCheck.is_available("http://localhost:11434") is False

@patch("platform.system")
@patch("subprocess.run")
@patch("subprocess.Popen")
def test_restart_service_mac_brew(mock_popen, mock_run, mock_system):
    mock_system.return_value = "Darwin"
    mock_run.return_value.returncode = 0 # success
    
    # 1st run call is pkill (ignored success)
    # 2nd run call is brew services
    
    assert OllamaHealthCheck.restart_service() is True
    # Verify brew connect called
    args_list = mock_run.call_args_list
    # Logic in code: if Darwin: try brew services.
    brew_call = [args[0][0] for args in args_list if args.args[0][0] == "brew"]
    assert len(brew_call) > 0

@patch("openai.OpenAI")
@patch("instructor.from_openai")
def test_factory_create_openai(mock_from_openai, mock_openai):
    try:
        LLMClientFactory.create(provider="openai", api_key="sk-test")
        mock_openai.assert_called_once()
        mock_from_openai.assert_called_once()
    except ImportError:
        pytest.skip("Dependencies not installed")

@patch("openai.OpenAI")
@patch("instructor.from_openai")
def test_factory_create_openrouter(mock_from_openai, mock_openai):
    try:
        LLMClientFactory.create(provider="openrouter", api_key="sk-or-test")
        mock_openai.assert_called_once()
        # Check base_url
        call_kwargs = mock_openai.call_args[1]
        assert "openrouter.ai" in call_kwargs.get("base_url", "")
    except ImportError:
        pytest.skip("Dependencies not installed")

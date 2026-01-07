"""
Centralized LLM Client Factory.
Handles initialization of Instructor-patched OpenAI clients for various providers.
Includes health checks for local providers.
"""
import os
import requests
from typing import Optional, Any, Dict

from .config import settings
from .utils import get_logger

logger = get_logger("LLMClient")

class OllamaHealthCheck:
    """Checks availability of local Ollama instance."""
    
    @staticmethod
    def is_available(base_url: str) -> bool:
        """Check if Ollama API is responsive."""
        try:
            # Simple check to /api/tags or version
            # Only checking connectivity here
            url = base_url.replace("/v1", "") # standard ollama api is at root/api
            if not url.endswith("/"):
                url += "/"
            
            # Check version
            resp = requests.get(f"{url}api/version", timeout=2.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mode: Optional[Any] = None 
    ) -> Any:
        """
        Create a configured Instructor client.
        
        Args:
            provider: 'openrouter', 'ollama', or 'openai'
            api_key: Override API key
            base_url: Override Base URL
            mode: Instructor mode (TOOLS, MD_JSON, etc.)
            
        Returns:
            Instructor-patched OpenAI client
        """
        try:
            import instructor
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install instructor openai")
            
        if provider == "ollama":
            return LLMClientFactory._create_ollama(api_key, base_url, mode)
        elif provider == "openrouter":
            return LLMClientFactory._create_openrouter(api_key, base_url, mode)
        else:
            return LLMClientFactory._create_openai(api_key, base_url, mode)

    @staticmethod
    def create_async(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mode: Optional[Any] = None
    ) -> Any:
        """Create a configured Async Instructor client."""
        try:
            import instructor
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("pip install instructor openai")

        client_args = LLMClientFactory._get_client_args(provider, api_key, base_url)
        
        # Determine mode
        if mode is None:
            if provider == "ollama":
                mode = instructor.Mode.JSON
            else:
                mode = instructor.Mode.TOOLS

        base_client = AsyncOpenAI(**client_args)
        return instructor.from_openai(base_client, mode=mode)

    @staticmethod
    def _create_ollama(api_key, base_url, mode):
        import instructor
        from openai import OpenAI
        
        url = base_url or settings.OLLAMA_BASE_URL
        
        # Health Check
        if not OllamaHealthCheck.is_available(url):
            logger.warning(f"Ollama appears down at {url}. Ensure 'ollama serve' is running.")
            
        client_args = {
            "base_url": url,
            "api_key": api_key or "ollama"
        }
        
        if mode is None:
            # Mode.TOOLS often fails with "multiple tool calls" error on local LLMs
            # Mode.JSON is more robust for Ollama/Llama3/Mistral
            mode = instructor.Mode.JSON
            
        return instructor.from_openai(OpenAI(**client_args), mode=mode)

    @staticmethod
    def _create_openrouter(api_key, base_url, mode):
        import instructor
        from openai import OpenAI
        
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set")
            
        client_args = {
            "base_url": base_url or "https://openrouter.ai/api/v1",
            "api_key": key
        }
        
        if mode is None:
            mode = instructor.Mode.TOOLS
            
        return instructor.from_openai(OpenAI(**client_args), mode=mode)

    @staticmethod
    def _create_openai(api_key, base_url, mode):
        import instructor
        from openai import OpenAI
        
        client_args = {
            "api_key": api_key or os.getenv("OPENAI_API_KEY")
        }
        if base_url:
            client_args["base_url"] = base_url
            
        if mode is None:
            mode = instructor.Mode.TOOLS
            
        return instructor.from_openai(OpenAI(**client_args), mode=mode)

    @staticmethod
    def _get_client_args(provider, api_key, base_url):
        """Helper to get args for Async client reuse."""
        # Reuse logic from Sync methods essentially
        if provider == "ollama":
            url = base_url or settings.OLLAMA_BASE_URL
            return {"base_url": url, "api_key": api_key or "ollama"}
        elif provider == "openrouter":
            key = api_key or os.getenv("OPENROUTER_API_KEY")
            return {"base_url": base_url or "https://openrouter.ai/api/v1", "api_key": key}
        else:
            return {"api_key": api_key or os.getenv("OPENAI_API_KEY")}

"""
Centralized LLM Client Factory.
Handles initialization of Instructor-patched OpenAI clients for various providers.
"""
import os
from typing import Optional, Any, Dict
import requests
from requests.exceptions import Timeout, ConnectionError

from .config import settings
from .utils import get_logger
from .platform_utils import OllamaServiceManager

logger = get_logger("LLMClient")

# Alias for backward compatibility if imported elsewhere
OllamaHealthCheck = OllamaServiceManager

class LLMClientFactory:
    """
    Factory for creating LLM clients (Sync and Async).
    """
    
    @staticmethod
    def create(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mode: Optional[Any] = None 
    ) -> Any:
        """
        Create a configured Instructor client (Synchronous).
        """
        try:
            import instructor
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install instructor openai")
            
        # 1. Get arguments
        client_args = LLMClientFactory._get_client_args(provider, api_key, base_url)
        
        # 2. Handle provider specifics (like side effects)
        if provider == "ollama":
            LLMClientFactory._ensure_ollama_available(client_args.get("base_url"))
            if mode is None:
                mode = instructor.Mode.JSON
        elif mode is None:
            # Default for cloud providers
            mode = instructor.Mode.TOOLS
            
        # 3. Create Client
        return instructor.from_openai(OpenAI(**client_args), mode=mode)

    @staticmethod
    def create_async(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mode: Optional[Any] = None
    ) -> Any:
        """
        Create a configured Instructor client (Asynchronous).
        """
        try:
            import instructor
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("pip install instructor openai")

        # 1. Get arguments
        client_args = LLMClientFactory._get_client_args(provider, api_key, base_url)
        
        # 2. Handle provider specifics
        if provider == "ollama":
            # Note: We check health even for async creation? Yes, usually good.
            # But async creation might want to avoid blocking calls. 
            # For now, we keep it consistent with sync, but maybe log warning if slow.
            LLMClientFactory._ensure_ollama_available(client_args.get("base_url"))
            if mode is None:
                mode = instructor.Mode.JSON
        elif mode is None:
            mode = instructor.Mode.TOOLS

        # 3. Create Client
        return instructor.from_openai(AsyncOpenAI(**client_args), mode=mode)

    @staticmethod
    def _get_client_args(provider: str, api_key: Optional[str], base_url: Optional[str]) -> Dict[str, Any]:
        """Resolve API Key and Base URL based on provider."""
        args = {}
        
        if provider == "ollama":
            args["base_url"] = base_url or settings.OLLAMA_BASE_URL
            args["api_key"] = api_key or "ollama"
            
        elif provider == "openrouter":
            key = api_key or settings.OPENROUTER_API_KEY
            if not key:
                 # We raise error here or let client fail? Better to fail early.
                 pass # ValueError("OPENROUTER_API_KEY") check was in old code
            if not key and not api_key:
                 # If no key provided at all
                 raise ValueError("OPENROUTER_API_KEY not set")
            
            args["base_url"] = base_url or settings.OPENROUTER_BASE_URL
            args["api_key"] = key
            
        else: # openai or generic
            args["api_key"] = api_key or settings.OPENAI_API_KEY
            if base_url:
                args["base_url"] = base_url
                
        return args

    @staticmethod
    def _ensure_ollama_available(url: Optional[str]) -> None:
        """Check and recover Ollama if needed."""
        target_url = url or settings.OLLAMA_BASE_URL
        try:
            if not OllamaServiceManager.is_available(target_url):
                logger.warning(f"Ollama appears down at {target_url}. Attempting auto-restart...")
                if OllamaServiceManager.restart_service():
                    # Poll for recovery
                    import time
                    for _ in range(settings.OLLAMA_RESTART_MAX_ATTEMPTS):
                        time.sleep(settings.OLLAMA_RESTART_POLL_INTERVAL)
                        if OllamaServiceManager.is_available(target_url):
                            logger.info("Ollama service successfully recovered!")
                            return
                    logger.error("Ollama restart initiated but service is still unresponsive.")
                else:
                    logger.error("Auto-restart failed. Please run 'ollama serve' manually.")
        except (Timeout, ConnectionError) as e:
            logger.error(f"Connection error checking Ollama status: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama status: {e}")
    
    # Backward compatibility helpers (if needed by old code using private methods)
    # _create_ollama, _create_openrouter etc. can be deprecated or proxied
    @staticmethod
    def _create_ollama(api_key, base_url, mode):
        """Deprecated: Use create('ollama', ...) instead."""
        # Bridge to new create logic
        return LLMClientFactory.create("ollama", api_key, base_url, mode)

    @staticmethod
    def _create_openrouter(api_key, base_url, mode):
        """Deprecated: Use create('openrouter', ...) instead."""
        return LLMClientFactory.create("openrouter", api_key, base_url, mode)

    @staticmethod
    def _create_openai(api_key, base_url, mode):
        """Deprecated: Use create('openai', ...) instead."""
        return LLMClientFactory.create("openai", api_key, base_url, mode)

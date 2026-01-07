#!/usr/bin/env python3
"""
Shared utilities for SR-Architect.

Contains:
- Environment variable loading
- Centralized LLM client initialization (Instructor/OpenAI)
"""

import os
import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List, Type, TypeVar

T = TypeVar("T")

from rich.logging import RichHandler

def setup_logging(level=None, log_file: Optional[Path] = None):
    """
    Configure organized logging with Rich and optional file output.
    """
    from .config import settings
    
    log_level = level or settings.LOG_LEVEL
    handlers: List[logging.Handler] = [RichHandler(rich_tracebacks=True)]
    
    if settings.LOG_FILE_ENABLED or log_file:
        path = log_file or (settings.LOG_DIR / f"sr_architect_{datetime.now().strftime('%Y%m%d')}.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True
    )

setup_logging()
logger = logging.getLogger("SR-Architect")

def get_logger(name: str):
    """Get a configured logger."""
    return logging.getLogger(name)


def load_env() -> None:
    """
    Load environment variables from .env files.
    
    Searches in:
    1. Current directory
    2. Parent directory
    3. User's Projects directory
    """
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent / ".env",
        Path.home() / "Projects" / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            logger.debug(f"Loading env from {env_path}")
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            return

# Core utilities should load env by default on import if needed, 
# but we'll stick to explicit calls in agents/core to be safe.
# load_env() 

def make_request(
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3,
) -> Any:
    """
    Centralized wrapper for external HTTP requests with logging and retries.
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    session.mount("http://", HTTPAdapter(max_retries=retry_strategy))

    logger.debug(f"Making {method} request to {url}")
    
    try:
        response = session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url} - {e}")
        raise RuntimeError(f"External API request failed: {e}")


class LLMCache:
    """Persistent JSON cache for LLM responses."""
    def __init__(self, cache_dir: str = ".cache/llm_responses"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_hash(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate a stable hash for a specific request."""
        # Clean messages and kwargs for hashing
        payload = {
            "model": model,
            "messages": messages,
            "params": {k: v for k, v in kwargs.items() if k != "response_model"}
        }
        dump = json.dumps(payload, sort_keys=True)
        return hashlib.md5(dump.encode()).hexdigest()

    def get(self, model: str, messages: List[Dict[str, Any]], response_model: Optional[Type[T]] = None, **kwargs) -> Optional[Any]:
        """Retrieve from cache with Pydantic support."""
        cache_hash = self._get_hash(model, messages, **kwargs)
        cache_path = self.cache_dir / f"{cache_hash}.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                if response_model and "pydantic" in data:
                    return response_model.model_validate_json(data["pydantic"])
                return data.get("raw")
            except Exception:
                return None
        return None 

    def set(self, model: str, messages: List[Dict[str, Any]], data: Any, **kwargs):
        """Save to cache with Pydantic support."""
        cache_hash = self._get_hash(model, messages, **kwargs)
        cache_path = self.cache_dir / f"{cache_hash}.json"
        
        payload = {}
        if hasattr(data, "model_dump_json"):
            payload["pydantic"] = data.model_dump_json()
        else:
            payload["raw"] = data
            
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            pass


def get_llm_client(
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Get a configured Instructor-patched OpenAI client (Sync).
    """
    try:
        import instructor
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "Required packages not installed. Run:\n"
            "pip install instructor openai"
        )
    
    load_env()
    client_args = _get_client_args(provider, api_key, base_url)
    
    try:
        base_client = OpenAI(**client_args)
        mode = instructor.Mode.MD_JSON if provider == "ollama" else instructor.Mode.TOOLS
        return instructor.from_openai(base_client, mode=mode)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize LLM client for {provider}: {e}")


def get_async_llm_client(
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Get a configured Instructor-patched AsyncOpenAI client.
    """
    try:
        import instructor
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError(
            "Required packages not installed. Run:\n"
            "pip install instructor openai"
        )
    
    load_env()
    client_args = _get_client_args(provider, api_key, base_url)
    
    try:
        base_client = AsyncOpenAI(**client_args)
        mode = instructor.Mode.MD_JSON if provider == "ollama" else instructor.Mode.TOOLS
        return instructor.from_openai(base_client, mode=mode)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Async LLM client for {provider}: {e}")


def _get_client_args(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to build client arguments for sync and async clients."""
    client_args = {}
    
    if provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set in environment or arguments.")
        
        client_args["base_url"] = base_url or "https://openrouter.ai/api/v1"
        client_args["api_key"] = key
        
    elif provider == "ollama":
        host = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        client_args["base_url"] = f"{host}/v1"
        client_args["api_key"] = "ollama"
        
    else:
        # Fallback for generic OpenAI usage
        client_args["api_key"] = api_key or os.getenv("OPENAI_API_KEY")
        if base_url:
            client_args["base_url"] = base_url
            
    return client_args


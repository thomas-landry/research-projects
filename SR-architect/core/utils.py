#!/usr/bin/env python3
"""
Shared utilities for SR-Architect.

Contains:
- Environment variable loading
- Centralized LLM client initialization (Instructor/OpenAI)
"""

import os
from pathlib import Path
from typing import Optional, Any
import logging

from rich.logging import RichHandler

def setup_logging(level=logging.INFO):
    """Configure rich logging."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
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


def get_llm_client(
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Get a configured Instructor-patched OpenAI client.
    
    Args:
        provider: "openrouter" or "ollama"
        api_key: Optional API key override
        base_url: Optional base URL override
        
    Returns:
        Instructor-patched OpenAI client
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

    try:
        base_client = OpenAI(**client_args)
        # Patch with Instructor for structured outputs
        return instructor.from_openai(base_client)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize LLM client for {provider}: {e}")

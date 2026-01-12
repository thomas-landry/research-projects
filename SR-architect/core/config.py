"""
Centralized Configuration for SR-Architect

CRITICAL: This is the ONLY place for configuration in the entire codebase.
All environment variables, API keys, model names, timeouts, and settings
MUST be defined here. Zero tolerance for scattered configuration.

Usage:
    from core.config import settings
    
    # Access settings
    api_key = settings.OPENROUTER_API_KEY
    model = settings.OPENROUTER_MODEL

Environment Variables:
    All settings can be overridden via .env file or environment variables.
    See .env.example for available options.

Default LLM:
    - Provider: OpenRouter (for API access to multiple models)
    - Model: Gemini 2.0 Flash Lite (low cost, high performance)
    - Fallback: Claude 3 Haiku (if Gemini fails)
"""

from typing import Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration for SR-Architect.
    
    All configuration must be defined here. This enforces:
    - Single source of truth for all settings
    - Type safety via Pydantic
    - Environment variable override support
    - Clear documentation of all options
    """
    
    # ========== API Keys ==========
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="OpenRouter API key for cloud LLM access"
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key (for direct OpenAI access)"
    )
    NCBI_EMAIL: str = Field(
        default="researcher@example.com",
        description="Email for NCBI API access (PubMed)"
    )
    NCBI_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional NCBI API key for higher rate limits"
    )
    
    # ========== LLM Provider Settings ==========
    LLM_PROVIDER: str = Field(
        default="openrouter",
        description="Default LLM provider (openrouter, openai, ollama)"
    )
    LLM_MODEL: Optional[str] = Field(
        default=None,
        description="Override default model selection"
    )
    
    # ========== Model Names ==========
    OPENROUTER_MODEL: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="Default OpenRouter model (Gemini for low cost)"
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.1:8b",
        description="Default Ollama local model"
    )
    FALLBACK_MODEL: str = Field(
        default="anthropic/claude-3-haiku",
        description="Fallback model if primary fails"
    )
    TWO_PASS_LOCAL_MODEL: str = Field(
        default="qwen3:14b",
        description="Local model for two-pass extraction (Pass 1)"
    )
    TWO_PASS_CLOUD_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Cloud model for two-pass extraction (Pass 2)"
    )
    
    # ========== Ollama Settings ==========
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434/v1",
        description="Ollama API base URL"
    )
    OLLAMA_HEALTH_CHECK_TIMEOUT: float = Field(
        default=2.0,
        description="Timeout for Ollama health check (seconds)"
    )
    OLLAMA_RESTART_POLL_INTERVAL: float = Field(
        default=2.0,
        description="Polling interval when restarting Ollama (seconds)"
    )
    OLLAMA_RESTART_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum restart attempts for Ollama"
    )
    PROCESS_KILL_GRACE_PERIOD: float = Field(
        default=1.0,
        description="Grace period before force-killing processes (seconds)"
    )
    
    # ========== Pipeline Settings ==========
    SCORE_THRESHOLD: float = Field(
        default=0.8,
        description="Minimum confidence score for extraction acceptance"
    )
    MAX_ITERATIONS: int = Field(
        default=3,
        description="Maximum extraction iterations per document"
    )
    MAX_CONTEXT_CHARS: int = Field(
        default=15000,
        description="Maximum context characters for LLM input"
    )
    HYBRID_MODE_DEFAULT: bool = Field(
        default=True,
        description="Enable hybrid local-first extraction by default"
    )
    
    # ========== Logging Settings ==========
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    LOG_FILE_ENABLED: bool = Field(
        default=True,
        description="Enable file logging"
    )
    
    # ========== Execution Settings ==========
    WORKERS: int = Field(
        default=4,
        description="Number of parallel workers for batch processing"
    )
    
    # ========== Paths ==========
    VECTOR_DIR: Path = Field(
        default=Path("./output/vector_store"),
        description="Directory for vector store persistence"
    )
    OUTPUT_DIR: Path = Field(
        default=Path("./output"),
        description="Directory for extraction outputs"
    )
    LOG_DIR: Path = Field(
        default=Path("./output/logs"),
        description="Directory for log files"
    )
    
    # ========== Pydantic Settings Config ==========
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore validation of extra env vars
        case_sensitive=True
    )


# Singleton instance - import this everywhere
settings = Settings()


# Model aliases for CLI convenience
MODEL_ALIASES = {
    "gemini": "google/gemini-2.0-flash-exp:free",
    "flash": "google/gemini-2.0-flash-exp:free",
    "sonnet": "anthropic/claude-3.5-sonnet",
    "haiku": "anthropic/claude-3-haiku",
    "gpt4o": "openai/gpt-4o",
    "llama3": "llama3.1:8b",
}


from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for SR-Architect.
    Reads from environment variables and .env files.
    """
    
    # LLM Settings
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: Optional[str] = None
    
    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    # Pipeline Settings
    SCORE_THRESHOLD: float = 0.8
    MAX_ITERATIONS: int = 3
    MAX_CONTEXT_CHARS: int = 15000
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_ENABLED: bool = True
    
    # Execution Settings
    WORKERS: int = 4
    
    # Paths
    VECTOR_DIR: Path = Path("./output/vector_store")
    OUTPUT_DIR: Path = Path("./output")
    LOG_DIR: Path = Path("./output/logs")
    
    # Config for pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore validation of extra env vars
    )

# Singleton instance
settings = Settings()

MODEL_ALIASES = {
    "gemini": "google/gemini-2.0-flash-lite-001",
    "flash": "google/gemini-2.0-flash-lite-001",
    "sonnet": "anthropic/claude-3.5-sonnet",
    "haiku": "anthropic/claude-3-haiku",
    "gpt4o": "openai/gpt-4o",
    "llama3": "llama3.1:8b",
}

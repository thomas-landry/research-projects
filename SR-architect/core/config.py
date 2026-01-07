
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
    
    # Pipeline Settings
    SCORE_THRESHOLD: float = 0.8
    MAX_ITERATIONS: int = 3
    MAX_CONTEXT_CHARS: int = 15000
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_ENABLED: bool = True
    
    # Execution Settings
    WORKERS: int = 1
    
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

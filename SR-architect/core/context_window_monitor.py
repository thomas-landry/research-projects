"""
Context Window Monitor to prevent LLM truncation.
Tracks token counts and warns when approaching limits.
"""
from typing import Optional, Dict, Any
from core.utils import get_logger

logger = get_logger("ContextWindowMonitor")

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed, using character-based estimation")


# Model context window limits (in tokens)
MODEL_CONTEXT_LIMITS = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "claude-3-sonnet": 200000,
    "claude-sonnet-4": 200000,
    "llama3.1:8b": 8192,
    "mistral": 32768,
    "qwen2.5-coder": 32768,
    "default": 8192,
}


class ContextWindowMonitor:
    """
    Monitors and manages context window usage to prevent truncation.
    """
    
    def __init__(
        self, 
        model: str = "default",
        safety_margin: float = 0.1,  # Reserve 10% for response
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize monitor.
        
        Args:
            model: Model name to lookup context limit
            safety_margin: Fraction of context to reserve for response
            encoding_name: Tiktoken encoding name
        """
        self.model = model
        self.safety_margin = safety_margin
        
        # Determine context limit
        self.context_limit = MODEL_CONTEXT_LIMITS.get(
            model.lower(), 
            MODEL_CONTEXT_LIMITS["default"]
        )
        self.usable_limit = int(self.context_limit * (1 - safety_margin))
        
        # Initialize tokenizer
        self._encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.warning(f"Could not load tiktoken encoder: {e}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Input text
            
        Returns:
            Token count
        """
        if not text:
            return 0
            
        if self._encoder:
            return len(self._encoder.encode(text))
        else:
            # Fallback: ~4 characters per token (rough estimate)
            return len(text) // 4
    
    def check_fits(self, text: str) -> bool:
        """
        Check if text fits within usable context window.
        
        Args:
            text: Input text
            
        Returns:
            True if text fits, False otherwise
        """
        tokens = self.count_tokens(text)
        fits = tokens <= self.usable_limit
        
        if not fits:
            logger.warning(
                f"Text ({tokens} tokens) exceeds usable limit ({self.usable_limit} tokens) "
                f"for model {self.model}"
            )
            
        return fits
    
    def truncate_to_fit(self, text: str, preserve_start: bool = True) -> str:
        """
        Truncate text to fit within context window.
        
        Args:
            text: Input text
            preserve_start: If True, keep start of text; else keep end
            
        Returns:
            Truncated text
        """
        if self.check_fits(text):
            return text
            
        tokens = self.count_tokens(text)
        excess_ratio = self.usable_limit / tokens
        
        # Estimate character limit
        char_limit = int(len(text) * excess_ratio * 0.95)  # 5% buffer
        
        if preserve_start:
            truncated = text[:char_limit]
            logger.info(f"Truncated text from {len(text)} to {len(truncated)} chars (preserving start)")
        else:
            truncated = text[-char_limit:]
            logger.info(f"Truncated text from {len(text)} to {len(truncated)} chars (preserving end)")
            
        return truncated
    
    def get_usage_report(self, text: str) -> Dict[str, Any]:
        """
        Get detailed usage report for text.
        
        Args:
            text: Input text
            
        Returns:
            Usage statistics
        """
        tokens = self.count_tokens(text)
        usage_pct = (tokens / self.usable_limit) * 100 if self.usable_limit > 0 else 0
        
        return {
            "tokens": tokens,
            "usable_limit": self.usable_limit,
            "context_limit": self.context_limit,
            "usage_percent": round(usage_pct, 1),
            "fits": tokens <= self.usable_limit,
            "model": self.model,
            "tiktoken_available": TIKTOKEN_AVAILABLE,
        }

"""
Text splitter wrapper using LangChain's RecursiveCharacterTextSplitter.
Provides robust text chunking capabilities.
"""

from typing import List, Optional

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fail fast if the dependency is missing (it should be in requirements.txt)
    raise ImportError(
        "langchain-text-splitters not installed. "
        "Please run: pip install langchain-text-splitters"
    )


class TextSplitter:
    """Wrapper for robust text splitting."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        """
        Initialize the text splitter.

        Args:
            chunk_size: Maximum size of chunks (in characters).
            chunk_overlap: Overlap between chunks (in characters).
            separators: List of separators to use for splitting. 
                        Defaults to ["\n\n", "\n", " ", ""].
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]
        
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks.

        Args:
            text: Input text to split.

        Returns:
            List of text chunks.
        """
        if not text:
            return []
        
        return self._splitter.split_text(text)


def split_text_into_chunks(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[str]:
    """
    Convenience function to split text.
    
    Args:
        text: Input text.
        chunk_size: Max chars per chunk.
        chunk_overlap: Overlap chars.
        
    Returns:
        List of chunks.
    """
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)

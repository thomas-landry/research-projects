#!/usr/bin/env python3
"""
Shim for backward compatibility.
DEPRECATED: Use core.parsers instead.
"""

from .parsers import DocumentParser, ParsedDocument, DocumentChunk

# Re-export for compatibility
__all__ = ["DocumentParser", "ParsedDocument", "DocumentChunk"]

if __name__ == "__main__":
    from .utils import setup_logging
    setup_logging()
    
    parser = DocumentParser()
    print("Parser initialized (via compatibility shim).")

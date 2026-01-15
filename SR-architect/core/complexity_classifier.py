"""
Complexity Classifier for PDF documents.
Determines parsing strategy based on document characteristics.
"""
import re
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import yaml

from core.utils import get_logger
from core.parsers.base import ParsedDocument

logger = get_logger("ComplexityClassifier")

# Default config path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "complexity_rules.yaml"


class ComplexityLevel(Enum):
    """Document complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ComplexityResult:
    """Result of complexity classification."""
    level: ComplexityLevel
    score: int
    signals: Dict[str, bool] = field(default_factory=dict)
    recommendations: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "score": self.score,
            "signals": self.signals,
            "recommendations": self.recommendations,
        }


class ComplexityClassifier:
    """
    Classifies document complexity to determine optimal parsing strategy.
    Rules are loaded from YAML configuration.
    """
    
    # Default thresholds if config not available
    DEFAULT_THRESHOLDS = {"simple": 3, "medium": 7, "complex": 100}
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize classifier.
        
        Args:
            config_path: Path to YAML config. Uses default if not provided.
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.debug(f"Loaded complexity config from {self.config_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
        else:
            logger.warning(f"Config not found at {self.config_path}. Using defaults.")
            
        # Return minimal default config
        return {
            "thresholds": self.DEFAULT_THRESHOLDS,
            "rules": {},
            "parser_recommendations": {
                "SIMPLE": {"primary": "pymupdf", "fallback": None, "use_ocr": False},
                "MEDIUM": {"primary": "docling", "fallback": "pymupdf", "use_ocr": False},
                "COMPLEX": {"primary": "docling", "fallback": "pdfplumber", "use_ocr": True},
            }
        }
    
    def classify(self, doc: ParsedDocument) -> ComplexityResult:
        """
        Classify document complexity.
        
        Args:
            doc: Parsed document to classify
            
        Returns:
            ComplexityResult with level, score, and recommendations
        """
        signals = {}
        score = 0
        rules = self.config.get("rules", {})
        
        # Check multi-column (heuristic: short lines with frequent breaks)
        if self._detect_multi_column(doc.full_text):
            signals["multi_column"] = True
            score += rules.get("multi_column", {}).get("weight", 2)
        else:
            signals["multi_column"] = False
            
        # Check for tables
        has_tables = self._detect_tables(doc)
        signals["has_tables"] = has_tables
        if has_tables:
            score += rules.get("has_tables", {}).get("weight", 3)
            
        # Check document length
        char_threshold = rules.get("short_text", {}).get("char_threshold", 5000)
        if len(doc.full_text) < char_threshold:
            signals["short_text"] = True
            score += rules.get("short_text", {}).get("weight", 1)
        else:
            signals["short_text"] = False
            
        # Check page count (if available)
        page_count = doc.metadata.get("page_count", 0)
        page_threshold = rules.get("long_document", {}).get("page_threshold", 30)
        if page_count > page_threshold:
            signals["long_document"] = True
            score += rules.get("long_document", {}).get("weight", 2)
        else:
            signals["long_document"] = False
            
        # Check for missing IMRAD sections
        if self._detect_missing_sections(doc.full_text):
            signals["missing_sections"] = True
            score += rules.get("missing_sections", {}).get("weight", 2)
        else:
            signals["missing_sections"] = False
            
        # Determine level from score
        thresholds = self.config.get("thresholds", self.DEFAULT_THRESHOLDS)
        if score <= thresholds.get("simple", 3):
            level = ComplexityLevel.SIMPLE
        elif score <= thresholds.get("medium", 7):
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.COMPLEX
            
        # Get recommendations
        recommendations = self.config.get("parser_recommendations", {}).get(
            level.name, 
            {"primary": "docling", "fallback": "pymupdf", "use_ocr": False}
        )
        
        logger.info(f"Document complexity: {level.value} (score={score})")
        
        return ComplexityResult(
            level=level,
            score=score,
            signals=signals,
            recommendations=recommendations,
        )
    
    def _detect_multi_column(self, text: str) -> bool:
        """Detect multi-column layout from text patterns."""
        if not text:
            return False
            
        lines = text.split('\n')
        if len(lines) < 10:
            return False
            
        # Heuristic: many short lines followed by similar-length lines
        short_line_count = sum(1 for line in lines if 20 < len(line.strip()) < 50)
        ratio = short_line_count / len(lines)
        
        return ratio > 0.4
    
    def _detect_tables(self, doc: ParsedDocument) -> bool:
        """Detect if document contains tables."""
        # Check metadata
        if doc.metadata.get("tables"):
            return True
            
        # Check chunks for table markers
        for chunk in doc.chunks:
            if chunk.chunk_type == "table":
                return True
            # Markdown table pattern
            if "|" in chunk.text and "---" in chunk.text:
                return True
                
        return False
    
    def _detect_missing_sections(self, text: str) -> bool:
        """Detect if standard academic sections are missing."""
        text_lower = text.lower()
        
        # Check for common section headers
        sections = ["abstract", "introduction", "method", "result", "discussion", "conclusion"]
        found = sum(1 for s in sections if s in text_lower)
        
        # If fewer than 3 sections found, consider it non-standard
        return found < 3
    
    def get_parser_strategy(self, doc: ParsedDocument) -> Dict[str, Any]:
        """
        Get recommended parser strategy for document.
        
        Returns:
            Dict with 'primary', 'fallback', and 'use_ocr' keys
        """
        result = self.classify(doc)
        return result.recommendations

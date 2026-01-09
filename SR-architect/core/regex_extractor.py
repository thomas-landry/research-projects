"""
Regex Extractor for Tier 0 field extraction.

Provides fast, deterministic extraction of well-formatted fields
before escalating to LLM extraction. Used as first pass in the
extraction cascade.

Supported fields:
- DOI
- publication_year
- case_count / sample_size
- patient_age (single value or range)
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core.utils import get_logger

logger = get_logger("RegexExtractor")


@dataclass
class RegexResult:
    """Result of a regex extraction."""
    field_name: str
    value: str
    confidence: float
    quote: str  # Context where match was found
    
    
# Pattern definitions with confidence scores
# Higher confidence for more specific patterns
FIELD_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    "doi": [
        # DOI in URL format
        (r'(?:https?://)?(?:dx\.)?doi\.org/([^\s,\]]+)', 0.98),
        # Standard DOI format with prefix
        (r'(?:doi|DOI)[:\s]+([^\s,\]]+)', 0.95),
        # Bare DOI pattern
        (r'\b(10\.\d{4,}/[^\s,\]]+)', 0.90),
    ],
    "publication_year": [
        # Year in copyright or publication context
        (r'(?:published|publication|received|accepted|copyright)[^\d]*(\d{4})', 0.95),
        # Year in citation format: Author et al. (2023)
        (r'et\s+al\.\s*\(?(\d{4})\)?', 0.92),
        # Year with explicit label
        (r'(?:year|published)[:\s]*(\d{4})', 0.90),
        # Standalone 4-digit year (less confident)
        (r'\b(20[0-2]\d)\b', 0.70),
    ],
    "case_count": [
        # N cases of...
        (r'(\d+)\s+cases?\s+(?:of|with|were)', 0.95),
        # N patients with...
        (r'(\d+)\s+patients?\s+(?:with|were|had)', 0.95),
        # N subjects
        (r'(\d+)\s+subjects?\b', 0.90),
        # Total of N patients
        (r'(?:total|included|identified)\s+(?:of\s+)?(\d+)\s+(?:patients?|cases?|subjects?)', 0.95),
    ],
    "sample_size": [
        # n=X format
        (r'[nN]\s*=\s*(\d+)', 0.98),
        # sample size of N
        (r'sample\s+size\s+(?:of|was)?\s*(\d+)', 0.95),
        # Study included N
        (r'study\s+included\s+(\d+)', 0.90),
    ],
    "patient_age": [
        # X-year-old format
        (r'(\d{1,3})-year-old', 0.98),
        # Age range: X to Y years
        (r'(?:ages?|aged)\s+(?:ranged?\s+)?(?:from\s+)?(\d{1,3})\s+to\s+(\d{1,3})', 0.95),
        # Mean/median age: X years
        (r'(?:mean|median|average)\s+age\s+(?:was|of)?\s*(\d{1,3}(?:\.\d+)?)', 0.95),
        # Age X years
        (r'age[d]?\s+(\d{1,3})\s*(?:years?)?', 0.88),
        # X years old
        (r'(\d{1,3})\s*(?:years?|yr)\s*(?:-)?old', 0.92),
    ],
}


class RegexExtractor:
    """
    Tier 0 extractor using regex patterns.
    
    Fast, deterministic extraction for well-formatted fields.
    Falls through to LLM extraction for low-confidence or missing fields.
    """
    
    def __init__(self, custom_patterns: Optional[Dict] = None):
        """
        Initialize extractor with optional custom patterns.
        
        Args:
            custom_patterns: Additional {field: [(pattern, confidence), ...]}
        """
        self.patterns = FIELD_PATTERNS.copy()
        if custom_patterns:
            for field, patterns in custom_patterns.items():
                if field in self.patterns:
                    self.patterns[field].extend(patterns)
                else:
                    self.patterns[field] = patterns
        
        # Compile patterns for performance
        self._compiled = {}
        for field, patterns in self.patterns.items():
            self._compiled[field] = [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in patterns
            ]
    
    def extract_field(
        self,
        field_name: str,
        text: str,
        context_chars: int = 100,
    ) -> Optional[RegexResult]:
        """
        Extract a single field from text.
        
        Args:
            field_name: Name of field to extract
            text: Source text
            context_chars: Characters of context to include in quote
            
        Returns:
            RegexResult if found, None otherwise
        """
        if field_name not in self._compiled:
            logger.debug(f"No patterns defined for field: {field_name}")
            return None
        
        best_result = None
        best_confidence = 0.0
        
        for pattern, base_confidence in self._compiled[field_name]:
            match = pattern.search(text)
            if match:
                # Handle groups - some patterns have multiple capture groups
                groups = match.groups()
                if len(groups) == 2 and field_name == "patient_age":
                    # Age range: combine min-max
                    value = f"{groups[0]}-{groups[1]}"
                else:
                    value = groups[0]
                
                # Clean value
                value = self._clean_value(field_name, value)
                
                # Calculate confidence based on match quality
                confidence = self._calculate_confidence(
                    base_confidence, match, text
                )
                
                if confidence > best_confidence:
                    # Extract context around match
                    start = max(0, match.start() - context_chars // 2)
                    end = min(len(text), match.end() + context_chars // 2)
                    quote = text[start:end].strip()
                    
                    best_result = RegexResult(
                        field_name=field_name,
                        value=value,
                        confidence=confidence,
                        quote=quote,
                    )
                    best_confidence = confidence
        
        if best_result:
            logger.debug(f"Regex extracted {field_name}: {best_result.value} (conf={best_confidence:.2f})")
        
        return best_result
    
    def extract_all(
        self,
        text: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, RegexResult]:
        """
        Extract all supported fields from text.
        
        Args:
            text: Source text
            fields: Optional list of specific fields to extract
            
        Returns:
            Dict of field_name -> RegexResult for successful extractions
        """
        target_fields = fields or list(self.patterns.keys())
        results = {}
        
        for field in target_fields:
            result = self.extract_field(field, text)
            if result:
                results[field] = result
        
        return results
    
    def _clean_value(self, field_name: str, value: str) -> str:
        """Clean extracted value based on field type."""
        value = value.strip()
        
        if field_name == "doi":
            # Remove trailing punctuation
            value = value.rstrip('.,;:)')
        elif field_name in ["case_count", "sample_size"]:
            # Remove any non-numeric characters
            value = re.sub(r'[^\d]', '', value)
        elif field_name == "publication_year":
            # Ensure 4-digit year
            match = re.search(r'(20[0-2]\d|19\d{2})', value)
            if match:
                value = match.group(1)
        
        return value
    
    def _calculate_confidence(
        self,
        base_confidence: float,
        match: re.Match,
        full_text: str,
    ) -> float:
        """
        Adjust confidence based on match context.
        
        Boosts confidence if match is in a "canonical" location
        (e.g., near keywords like "DOI:", "age:", etc.)
        """
        # Get surrounding context
        start = max(0, match.start() - 50)
        context = full_text[start:match.end()].lower()
        
        # Boost for keyword proximity
        confidence = base_confidence
        
        boost_keywords = {
            "doi": ["doi", "digital object", "https://doi"],
            "publication_year": ["published", "year", "copyright"],
            "case_count": ["cases", "patients", "subjects", "included"],
            "sample_size": ["sample", "n=", "participants"],
            "patient_age": ["age", "year-old", "years old"],
        }
        
        field = match.re.pattern  # This is a rough heuristic
        for kw in boost_keywords.get("doi", []):  # Default check
            if kw in context:
                confidence = min(1.0, confidence + 0.02)
                break
        
        return min(1.0, confidence)
    
    @property
    def supported_fields(self) -> List[str]:
        """Return list of supported field names."""
        return list(self.patterns.keys())


import re
from typing import Dict, List, Tuple
from core.utils import get_logger

logger = get_logger("IMRADParser")

class IMRADParser:
    """
    Parses scientific text into IMRAD sections (Introduction, Methods, Results, Discussion)
    using regex heuristics.
    """
    
    # Regex patterns for section headers
    # We look for lines that are likely headers (short, bold-like, numbered)
    # Note: These are case-insensitive
    PATTERNS = {
        "introduction": r"^(?:1\.?|I\.?)?\s*(?:introduction|background|objective)",
        "methods": r"^(?:2\.?|II\.?)?\s*(?:methods|materials|methodology|patients\s+and\s+methods|study\s+design)",
        "results": r"^(?:3\.?|III\.?)?\s*(?:results|findings|clinical\s+course|case\s+presentation|case\s+report)",
        "discussion": r"^(?:4\.?|IV\.?)?\s*(?:discussion|comment|conclusion|summary)",
        "references": r"^(?:5\.?|V\.?)?\s*(?:references|bibliography|acknowledgements|funding)"
    }

    def __init__(self):
        self.compiled_patterns = {
            k: re.compile(v, re.IGNORECASE | re.MULTILINE) 
            for k, v in self.PATTERNS.items()
        }

    def parse(self, text: str) -> Dict[str, str]:
        """
        Segment text into IMRAD sections.
        
        Args:
            text: Full document text
            
        Returns:
            Dictionary with keys: abstract, introduction, methods, results, discussion
        """
        sections = {
            "abstract": "",
            "introduction": "",
            "methods": "",
            "results": "",
            "discussion": "",
            "uncategorized": ""
        }
        
        lines = text.split('\n')
        current_section = "uncategorized"
        buffer = []
        
        # Simple Abstract detection (usually at start)
        # We'll treat the start of the doc as Abstract/Uncategorized until we hit Intro
        
        for line in lines:
            normalized_line = line.strip().lower()
            if not normalized_line:
                buffer.append(line)
                continue
                
            # Check for section headers
            # Heuristic: headers are usually short (< 50 chars)
            if len(normalized_line) < 50:
                new_section = None
                
                # Check explicit Abstract header
                if re.match(r"^abstract\b", normalized_line):
                    new_section = "abstract"
                else:
                    for section_name, pattern in self.compiled_patterns.items():
                        if pattern.match(normalized_line):
                            new_section = section_name
                            # Special handling: 'References' stops the IMRAD parsing
                            if section_name == "references":
                                new_section = "REFERENCES_STOP"
                            break
                
                if new_section:
                    # Flush buffer to current section
                    sections[current_section] += "\n".join(buffer) + "\n"
                    buffer = []
                    
                    if new_section == "REFERENCES_STOP":
                        # We are done, ignore the rest or store as footer? 
                        # For extraction purposes, we can stop or map to uncategorized
                        # Let's break to avoid cluttering context with refs
                        # But wait, we need to handle the case where we want to keep it?
                        # Plan said "Smart Section Filtering" is later task. 
                        # For IMRAD, we just segment.
                        current_section = "uncategorized" # fallback
                    else:
                        current_section = new_section
                    
                    # Don't add the header line itself to the text strictly? 
                    # Usually better to keep it for context, but maybe marked?
                    buffer.append(line) 
                    continue

            buffer.append(line)
            
        # Flush remaining
        sections[current_section] += "\n".join(buffer)
        
        return {k: v.strip() for k, v in sections.items()}

    def get_extraction_context(self, sections: Dict[str, str], max_chars: int = 15000) -> str:
        """
        Construct an optimized context from parsed sections.
        Prioritizes Results > Methods > Abstract > Discussion > Intro.
        """
        context = []
        
        # 1. Abstract (High density)
        if sections["abstract"]:
            context.append(f"ABSTRACT:\n{sections['abstract']}")
            
        # 2. Results (Critical data)
        if sections["results"]:
            context.append(f"RESULTS:\n{sections['results']}")
            
        # 3. Methods (Critical context)
        if sections["methods"]:
            context.append(f"METHODS:\n{sections['methods']}")
            
        # 4. Discussion (Interpretations, sometimes contains data not in results)
        if sections["discussion"]:
            context.append(f"DISCUSSION:\n{sections['discussion']}")
            
        # 5. Case Presentation (often mapped to Results, but if separate/uncategorized?)
        # If uncategorized is large and others are empty, use it (fallback)
        total_structured = sum(len(sections[k]) for k in ["abstract", "methods", "results", "discussion"])
        if total_structured < 500 and sections["uncategorized"]:
            context.append(f"FULL TEXT (Uncategorized):\n{sections['uncategorized']}")
            
        return "\n\n".join(context)[:max_chars]

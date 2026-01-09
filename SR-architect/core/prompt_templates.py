"""
Prompt Template Manager for schema-aware extraction.

Loads field-specific templates with few-shot examples
and extraction rules to improve LLM extraction accuracy.

Per plan.md: Create prompt templates per field type.
"""
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from core.utils import get_logger

logger = get_logger("PromptTemplates")

# Default templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "prompts" / "field_templates"


@dataclass
class FieldTemplate:
    """Template for a specific field extraction."""
    name: str
    description: str
    field_type: str
    extraction_rules: List[str]
    few_shot_examples: List[Dict[str, Any]]
    allowed_values: Optional[List[str]] = None


class PromptTemplateManager:
    """
    Manages field-specific prompt templates for extraction.
    
    Loads YAML templates containing:
    - Field descriptions
    - Extraction rules
    - Few-shot examples
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Directory containing YAML template files
        """
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._templates: Dict[str, FieldTemplate] = {}
        self._loaded = False
        
    def load_templates(self, filename: str = "systematic_review.yaml"):
        """Load templates from a YAML file."""
        template_path = self.templates_dir / filename
        
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}")
            return
        
        with open(template_path, "r") as f:
            data = yaml.safe_load(f)
        
        for field_name, config in data.items():
            if isinstance(config, dict) and "description" in config:
                self._templates[field_name] = FieldTemplate(
                    name=field_name,
                    description=config.get("description", ""),
                    field_type=config.get("field_type", "text"),
                    extraction_rules=config.get("extraction_rules", []),
                    few_shot_examples=config.get("few_shot_examples", []),
                    allowed_values=config.get("allowed_values"),
                )
        
        self._loaded = True
        logger.info(f"Loaded {len(self._templates)} field templates from {filename}")
    
    def get_template(self, field_name: str) -> Optional[FieldTemplate]:
        """Get template for a specific field."""
        if not self._loaded:
            self.load_templates()
        return self._templates.get(field_name)
    
    def get_extraction_prompt(
        self,
        field_name: str,
        context: str,
        include_examples: bool = True,
    ) -> str:
        """
        Generate a field-specific extraction prompt.
        
        Args:
            field_name: Field to extract
            context: Document text
            include_examples: Whether to include few-shot examples
            
        Returns:
            Formatted prompt string
        """
        template = self.get_template(field_name)
        
        if not template:
            # Fallback to basic prompt
            return self._basic_prompt(field_name, context)
        
        # Build structured prompt
        prompt_parts = [
            f"# Extract: {field_name}",
            f"\n## Description\n{template.description}",
        ]
        
        # Add extraction rules
        if template.extraction_rules:
            prompt_parts.append("\n## Extraction Rules")
            for rule in template.extraction_rules:
                prompt_parts.append(f"- {rule}")
        
        # Add allowed values for categorical fields
        if template.allowed_values:
            prompt_parts.append(f"\n## Allowed Values\n{', '.join(template.allowed_values)}")
        
        # Add few-shot examples
        if include_examples and template.few_shot_examples:
            prompt_parts.append("\n## Examples")
            for example in template.few_shot_examples[:3]:  # Max 3 examples
                prompt_parts.append(f"\nInput: \"{example.get('input', '')}\"")
                prompt_parts.append(f"Output: {example.get('output', '')}")
                if "quote" in example:
                    prompt_parts.append(f"Quote: \"{example.get('quote', '')}\"")
        
        # Add context
        prompt_parts.append(f"\n## Document Text\n{context[:5000]}")  # Truncate
        
        prompt_parts.append(f"\n## Task\nExtract the value for '{field_name}' from the document.")
        prompt_parts.append("Return the value and a supporting quote from the text.")
        
        return "\n".join(prompt_parts)
    
    def _basic_prompt(self, field_name: str, context: str) -> str:
        """Basic extraction prompt without template."""
        return f"""Extract the value for '{field_name}' from the following text.
Return the extracted value and a supporting quote.

Text:
{context[:5000]}
"""
    
    def get_available_fields(self) -> List[str]:
        """Get list of fields with templates."""
        if not self._loaded:
            self.load_templates()
        return list(self._templates.keys())
    
    def has_template(self, field_name: str) -> bool:
        """Check if a template exists for a field."""
        return self.get_template(field_name) is not None

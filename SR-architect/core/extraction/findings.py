"""
Findings Extraction.

Batch extraction of structured findings from narrative text using instructor.
"""

from typing import List, Dict, Any, Type
from pydantic import create_model, BaseModel

from core.fields.spec import ColumnSpec
from core.types.models import FindingReport
from core.client import LLMClientFactory
from core.config import settings

async def extract_findings_batch(
    narrative: str,
    specs: List[ColumnSpec],
) -> Dict[str, FindingReport]:
    """
    Extract multiple findings from single narrative using LLM.
    
    Args:
        narrative: Source text
        specs: List of column specs to extract
        
    Returns:
        Dictionary of key -> FindingReport
    """
    # 1. Build Dynamic Pydantic Model from Specs
    # This tells instructor exactly what schema to expect
    field_definitions = {
        spec.key: (spec.dtype, spec.to_field()) 
        for spec in specs
    }
    
    DynamicExtractionModel = create_model(
        "DynamicExtractionModel",
        **field_definitions
    )
    
    # 2. Initialize LLM Client
    client = LLMClientFactory.create_async(provider=settings.LLM_PROVIDER)
    model_name = settings.get_model_for_provider()
    
    # 3. Construct System Prompt
    system_prompt = (
        "You are an expert systematic review data extractor. "
        "Extract the requested findings from the text accurately. "
        "For binary/frequency findings, determine the status (present/absent/etc) "
        "and extract specific counts (n/N) if available. "
        "If a finding is not mentioned, use status='not_reported'."
    )
    
    try:
        print(f"DEBUG: Using provider={settings.LLM_PROVIDER}, model={model_name}")
        print(f"DEBUG: DynamicModel schema: {DynamicExtractionModel.model_json_schema()}")
        
        # 4. Execute Extraction
        response = await client.chat.completions.create(
            model=model_name,
            response_model=DynamicExtractionModel,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to extract from:\n\n{narrative}"}
            ],
            max_retries=2,
        )
        
        # 5. Return as Dict
        # model_dump() returns the populated fields
        return response.model_dump()
        
    except Exception as e:
        # Log error in production, distinct from fallback
        print(f"Extraction failed: {e}")
        return {}

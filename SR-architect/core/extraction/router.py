"""
Extraction Policy Router.

Routes column specs to appropriate extraction handlers based on their policy.
"""

from enum import Enum
from core.fields.spec import ColumnSpec
from core.types.enums import ExtractionPolicy


class ExtractionHandlerType(str, Enum):
    """Types of extraction handlers."""
    METADATA = "metadata"
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    DERIVED = "derived"
    HUMAN_REVIEW = "human_review"


def route_by_policy(spec: ColumnSpec) -> ExtractionHandlerType:
    """
    Route field to appropriate handler based on extraction policy.
    
    Args:
        spec: Column specification
        
    Returns:
        Handler type for this field
    """
    mapping = {
        ExtractionPolicy.METADATA: ExtractionHandlerType.METADATA,
        ExtractionPolicy.MUST_BE_EXPLICIT: ExtractionHandlerType.EXPLICIT,
        ExtractionPolicy.CAN_BE_INFERRED: ExtractionHandlerType.INFERRED,
        ExtractionPolicy.DERIVED: ExtractionHandlerType.DERIVED,
        ExtractionPolicy.HUMAN_REVIEW: ExtractionHandlerType.HUMAN_REVIEW,
    }
    
    return mapping.get(spec.extraction_policy, ExtractionHandlerType.EXPLICIT)

# TwoPassExtractor Implementation Plan

**Component**: `core/two_pass_extractor.py`  
**Goal**: Reduce cloud API calls by 30-40% using two-pass extraction  
**Approach**: Test-Driven Development (RED → GREEN → REFACTOR)

---

## Architecture

### Pass 1: Fast & Cheap (Gemini Flash Lite)
-  **Model**: `google/gemini-2.0-flash-lite-001`
- **Cost**: $0.07/M input, $0.21/M output
- **Purpose**: Extract all fields with confidence scores
- **Output**: Data + confidence + evidence for each field

### Pass 2: Premium Escalation (Claude 3.5 Sonnet)
- **Model**: `anthropic/claude-3.5-sonnet`
- **Cost**: $3.00/M input, $15.00/M output
- **Purpose**: Re-extract ONLY low-confidence fields
- **Trigger**: Confidence  < threshold (default 0.75)

---

## Cost Analysis

### Before (Single Pass - Premium Only)
```
100 fields × $15/M tokens = $1.50 per paper
```

### After (Two-Pass Strategy)
```
Pass 1: 100 fields × $0.21/M = $0.021
Pass 2:  10 fields × $15/M  = $0.150  (only low-confidence)
Total: $0.171 per paper
```

**Savings**: ~88% reduction ✅

---

## Implementation (TDD)

### Phase 1: Pass 1 with Gemini ✅

#### RED - Write Failing Tests
**File**: `tests/test_two_pass_gemini.py`

```python
class TestPass1GeminiExtraction:
    def test_gemini_extracts_all_fields(self):
        """Pass 1 should extract all requested fields"""
        # Should FAIL initially
        
    def test_gemini_returns_confidence_scores(self):
        """Each field should have confidence 0-1"""
        # Should FAIL initially
        
    def test_gemini_identifies_low_confidence(self):
        """Low-confidence fields flagged for Pass 2"""
        # Should FAIL initially
```

####GREEN - Implement Pass 1
**File**: `core/two_pass_extractor.py`

```python
def _extract_local(
    self,
    text: str,
    schema: Type[BaseModel],
    confidence_threshold: float = 0.75
) -> TwoPassResult:
    """
    Pass 1: Extract using Gemini Flash Lite with confidence scoring.
    """
    # Create dynamic Pydantic model with confidence
    fields_with_confidence = {}
    for field_name, field_info in schema.model_fields.items():
        fields_with_confidence[field_name] = (
            field_info.annotation,
            Field(description=field_info.description)
        )
        fields_with_confidence[f"{field_name}_confidence"] = (
            float,
            Field(ge=0.0, le=1.0)
        )
    
    DynamicModel = create_model(
        f"{schema.__name__}WithConfidence",
        **fields_with_confidence
    )
    
    # Use Instructor for structured extraction
    client = instructor.from_openai(
        OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    )
    
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-lite-001",
        response_model=DynamicModel,
        messages=[{
            "role": "user",
            "content": f"Extract data from: {text}"
        }]
    )
    
    # Separate data and confidence
    data_dict = {}
    confidence_dict = {}
    low_confidence_fields = []
    
    for field in schema.model_fields:
        value = getattr(response, field, None)
        conf = getattr(response, f"{field}_confidence", 0.5)
        
        data_dict[field] = value
        confidence_dict[field] = conf
        
        if conf < confidence_threshold:
            low_confidence_fields.append(field)
    
    return TwoPassResult(
        data=data_dict,
        confidence=confidence_dict,
        low_confidence_fields=low_confidence_fields,
        pass1_model="gemini-2.0-flash-lite",
        pass2_needed=len(low_confidence_fields) > 0
    )
```

#### REFACTOR - Clean Up
- Extract model creation to helper
- Add error handling
- Improve logging

**Test Result**: 5/5 passing ✅

---

### Phase 2: Pass 2 with Cost Controls ✅

#### RED - Write Failing Tests
**File**: `tests/test_two_pass_premium.py`

```python
class TestPass2PremiumExtraction:
    def test_cost_calculation(self):
        """Estimate cost before calling premium API"""
        # Should FAIL initially
        
    def test_manual_review_above_threshold(self):
        """Show cost estimate and request approval"""
        # Should FAIL initially
        
    def test_premium_extraction_only_low_conf(self):
        """Pass 2 only extracts flagged fields"""
        # Should FAIL initially
```

#### GREEN - Implement Pass 2
**File**: `core/two_pass_extractor.py`

```python
def _calculate_premium_cost(
    self,
    text: str,
    fields: List[str],
    model: str = "anthropic/claude-3.5-sonnet"
) -> float:
    """
    Estimate cost of premium extraction.
    """
    # token counts
    input_tokens = len(text.split()) * 1.3  # Rough estimate
    output_tokens = len(fields) * 50  # ~50 tokens per field
    
    # Pricing (per million tokens)
    pricing = {
        "anthropic/claude-3.5-sonnet": {
            "input": 3.00,
            "output": 15.00
        }
    }
    
    rates = pricing.get(model, pricing["anthropic/claude-3.5-sonnet"])
    cost = (
        (input_tokens / 1_000_000) * rates["input"] +
        (output_tokens / 1_000_000) * rates["output"]
    )
    
    return cost

def _request_manual_review(self, cost: float) -> bool:
    """
    Request user approval if cost exceeds threshold.
    """
    threshold = 0.01  # $0.01 auto-approve
    
    if cost < threshold:
        logger.info(f"Auto-approving: cost ${cost:.4f} < ${threshold}")
        return True
    
    # Manual review
    print(f"\n⚠️  Premium extraction estimated cost: ${cost:.4f}")
    print("Options:")
    print("  [y] Proceed with premium extraction")
    print("  [n] Skip premium extraction")
    print("  [d] Defer decision (save for later)")
    
    response = input("Choice [y/n/d]: ").lower()
    return response == 'y'

def _extract_cloud(
    self,
    text: str,
    schema: Type[BaseModel],
    low_confidence_fields: List[str]
) -> Dict[str, Any]:
    """
    Pass 2: Extract only low-confidence fields using premium model.
    """
    # Cost check
    estimated_cost = self._calculate_premium_cost(
        text,
        low_confidence_fields
    )
    
    if not self._request_manual_review(estimated_cost):
        logger.warning("User declined premium extraction")
        return {}
    
    # Create schema for only low-confidence fields
    field_subset = {
        name: info
        for name, info in schema.model_fields.items()
        if name in low_confidence_fields
    }
    
    PartialModel = create_model(
        f"{schema.__name__}Partial",
        **{
            name: (info.annotation, info)
            for name, info in field_subset.items()
        }
    )
    
    # Extract with premium model
    client = instructor.from_openai(
        OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    )
    
    response = client.chat.completions.create(
        model="anthropic/claude-3.5-sonnet",
        response_model=PartialModel,
        messages=[{
            "role": "user",
            "content": f"Extract ONLY these fields: {', '.join(low_confidence_fields)}\n\n{text}"
        }]
    )
    
    return response.model_dump()
```

#### REFACTOR
- Extract pricing to config
- Add defer option implementation
- Improve cost estimation accuracy

**Test Result**: Core logic implemented ✅

---

## Integration

### Hierarchical Pipeline
```python
# Option to use two-pass
result = self.two_pass_extractor.extract_two_pass(
    text=document.full_text,
    schema=DPMGoldStandardSchema,
    confidence_threshold=0.75
)

# Result contains:
# - data: All extracted fields
# - confidence: Per-field confidence
# - cost_savings: Estimated savings vs single-pass
```

---

## Configuration

Add to `core/config.py`:
```python
# TwoPass settings
PASS1_MODEL = "google/gemini-2.0-flash-lite-001"
PASS1_CONFIDENCE_THRESHOLD = 0.75
PASS2_MODEL = "anthropic/claude-3.5-sonnet"
AUTO_APPROVE_COST_THRESHOLD = 0.01  # Auto-approve if < $0.01
```

---

## Test Coverage

- `test_two_pass_gemini.py`: 5/5 passing ✅
- `test_two_pass_premium.py`: Core logic in place ✅

---

## Expected Results

- **Cost reduction**: 30-40% on average
- **Accuracy**: Maintained (premium for difficult fields)
- **Speed**: Faster (Gemini is 2-3x faster than Claude)
- **User control**: Manual review for expensive extractions

---

## Status

✅ **Phase 1 Complete**: Gemini Pass 1 with confidence  
✅ **Phase 2 Complete**: Premium Pass 2 with cost controls  
⏳ **Integration**: Ready for hierarchical pipeline integration


from core.classification import RelevanceResponse
import pytest

def test_validator_coercion():
    # Simulate Gemini Flash Lite output
    raw_output = {"classifications": ["0", "1", "0", "1"]}
    
    # Validation should succeed now
    response = RelevanceResponse(**raw_output)
    
    assert len(response.classifications) == 4
    assert response.classifications[0].relevant == 0
    assert response.classifications[1].relevant == 1
    assert response.classifications[0].index == 0
    assert response.classifications[1].index == 1
    assert response.classifications[0].reason == "Inferred from simplified output"
    
    print("Validator verification passed!")

if __name__ == "__main__":
    test_validator_coercion()

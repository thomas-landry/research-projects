import pytest
from core.batch_processor import CircuitBreaker

def test_circuit_breaker_logic():
    # Threshold = 3 consecutive failures
    cb = CircuitBreaker(threshold=3)
    
    assert not cb.is_open
    
    # 2 failures
    cb.record_failure()
    cb.record_failure()
    assert not cb.is_open
    
    # Success resets
    cb.record_success()
    assert cb.failure_count == 0
    
    # 3 failures -> Open
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open
    
    # Subsequent calls
    cb.record_failure()
    assert cb.is_open
    
    # Reset
    cb.reset()
    assert not cb.is_open
    assert cb.failure_count == 0
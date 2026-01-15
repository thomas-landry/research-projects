"""
Circuit breaker for batch processing.
"""
import threading

class CircuitBreaker:
    """
    Circuit breaker to stop processing or switch modes after consecutive failures.
    """
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.failure_count = 0
        self.is_open = False
        self._lock = threading.Lock()
        
    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.threshold:
                self.is_open = True
            
    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.is_open = False
        
    def reset(self):
        with self._lock:
            self.failure_count = 0
            self.is_open = False

"""
Circuit breaker for batch processing.
"""
import threading

DEFAULT_THRESHOLD = 3

class CircuitBreaker:
    """
    Circuit breaker to stop processing or switch modes after consecutive failures.
    
    Thread-safe implementation that tracks consecutive failures and opens
    the circuit when the threshold is reached.
    """
    def __init__(self, threshold: int = DEFAULT_THRESHOLD):
        """
        Initialize the circuit breaker.
        
        Args:
            threshold: Number of consecutive failures before opening the circuit.
        """
        self.threshold = threshold
        self.failure_count = 0
        self._is_open = False
        self._lock = threading.Lock()
        
    @property
    def is_open(self) -> bool:
        """Check if the circuit is open (thread-safe)."""
        with self._lock:
            return self._is_open
        
    def record_failure(self) -> None:
        """Record a failure and check if threshold is reached."""
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.threshold:
                self._is_open = True
            
    def record_success(self) -> None:
        """Record a success and reset the failure count."""
        self.reset()
        
    def reset(self) -> None:
        """Reset the circuit breaker state (close circuit, zero failures)."""
        with self._lock:
            self.failure_count = 0
            self._is_open = False

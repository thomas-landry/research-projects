"""
Unit tests for ExecutionHandler class.

Tests the shared execution logic used by BatchExecutor for both
sync and async execution paths.
"""
import pytest
from unittest.mock import Mock, MagicMock
from core.batch import ExecutionHandler, CircuitBreaker
from core.state_manager import StateManager


class TestExecutionHandlerSerializeResult:
    """Test result serialization logic."""
    
    def test_serialize_result_with_to_dict(self):
        """Should use to_dict() method if available."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        mock_result = Mock()
        mock_result.to_dict.return_value = {"field": "value"}
        
        # Act
        serialized = handler.serialize_result(mock_result)
        
        # Assert
        assert serialized == {"field": "value"}
        mock_result.to_dict.assert_called_once()
    
    def test_serialize_result_with_model_dump(self):
        """Should use model_dump() if to_dict() not available."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        mock_result = MagicMock()
        del mock_result.to_dict  # Remove to_dict to force model_dump path
        mock_result.model_dump.return_value = {"field": "value"}
        
        # Act
        serialized = handler.serialize_result(mock_result)
        
        # Assert
        assert serialized == {"field": "value"}
        mock_result.model_dump.assert_called_once()
    
    def test_serialize_result_with_dict(self):
        """Should return dict as-is."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        result = {"field": "value"}
        
        # Act
        serialized = handler.serialize_result(result)
        
        # Assert
        assert serialized == {"field": "value"}
        assert serialized is result  # Same object
    
    def test_serialize_result_with_object(self):
        """Should use __dict__ as fallback."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        class SimpleObject:
            def __init__(self):
                self.field = "value"
        
        result = SimpleObject()
        
        # Act
        serialized = handler.serialize_result(result)
        
        # Assert
        assert serialized == {"field": "value"}


class TestExecutionHandlerSuccess:
    """Test success handling."""
    
    def test_handle_success_updates_state(self):
        """Should update state manager with success status."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        filename = "test.pdf"
        serialized = {"field": "value"}
        
        # Act
        result = handler.handle_success(filename, serialized)
        
        # Assert
        state_manager.update_result.assert_called_once_with(
            filename, serialized, status="success", save=True
        )
        assert result == (filename, serialized, "success")
    
    def test_handle_success_records_circuit_breaker_success(self):
        """Should record success in circuit breaker."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        # Act
        handler.handle_success("test.pdf", {"field": "value"})
        
        # Assert
        circuit_breaker.record_success.assert_called_once()
    
    def test_handle_success_calls_callback(self):
        """Should call progress callback if provided."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        callback = Mock()
        
        filename = "test.pdf"
        serialized = {"field": "value"}
        
        # Act
        handler.handle_success(filename, serialized, callback=callback)
        
        # Assert
        callback.assert_called_once_with(filename, serialized, "success")
    
    def test_handle_success_with_save_false(self):
        """Should pass save=False to state manager when specified."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        # Act
        handler.handle_success("test.pdf", {"field": "value"}, save=False)
        
        # Assert
        state_manager.update_result.assert_called_once_with(
            "test.pdf", {"field": "value"}, status="success", save=False
        )


class TestExecutionHandlerMemoryError:
    """Test memory error handling."""
    
    def test_handle_memory_error_updates_state(self):
        """Should update state with memory error payload."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        filename = "test.pdf"
        
        # Act
        result = handler.handle_memory_error(filename)
        
        # Assert
        expected_payload = {"error": "Out of memory", "error_type": "MemoryError"}
        state_manager.update_result.assert_called_once_with(
            filename, expected_payload, status="failed", save=True
        )
        assert result == (filename, expected_payload, "failed")
    
    def test_handle_memory_error_records_circuit_breaker_failure(self):
        """Should record failure in circuit breaker."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        # Act
        handler.handle_memory_error("test.pdf")
        
        # Assert
        circuit_breaker.record_failure.assert_called_once()
    
    def test_handle_memory_error_calls_callback(self):
        """Should call progress callback if provided."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        callback = Mock()
        
        # Act
        handler.handle_memory_error("test.pdf", callback=callback)
        
        # Assert
        expected_payload = {"error": "Out of memory", "error_type": "MemoryError"}
        callback.assert_called_once_with("test.pdf", expected_payload, "failed")


class TestExecutionHandlerGeneralError:
    """Test general error handling."""
    
    def test_handle_general_error_updates_state(self):
        """Should update state with error message."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        filename = "test.pdf"
        error = ValueError("Invalid input")
        
        # Act
        result = handler.handle_general_error(filename, error)
        
        # Assert
        expected_payload = {"error": "Invalid input"}
        state_manager.update_result.assert_called_once_with(
            filename, expected_payload, status="failed", save=True
        )
        assert result == (filename, expected_payload, "failed")
    
    def test_handle_general_error_records_circuit_breaker_failure(self):
        """Should record failure in circuit breaker."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        # Act
        handler.handle_general_error("test.pdf", ValueError("test"))
        
        # Assert
        circuit_breaker.record_failure.assert_called_once()
    
    def test_handle_general_error_calls_callback(self):
        """Should call progress callback if provided."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        callback = Mock()
        
        error = ValueError("test error")
        
        # Act
        handler.handle_general_error("test.pdf", error, callback=callback)
        
        # Assert
        callback.assert_called_once_with("test.pdf", "test error", "failed")
    
    def test_handle_general_error_with_error_registry(self):
        """Should register error when register_error=True."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        error = ValueError("test error")
        
        # Act
        from unittest.mock import patch
        with patch('core.error_registry.ErrorRegistry') as mock_registry:
            handler.handle_general_error(
                "test.pdf", error, register_error=True
            )
            
            # Assert
            mock_registry.return_value.register.assert_called_once_with(
                error,
                location="BatchExecutor.process_batch_async",
                context={"filename": "test.pdf"}
            )
    
    def test_handle_general_error_without_error_registry(self):
        """Should not register error when register_error=False."""
        # Arrange
        state_manager = Mock(spec=StateManager)
        circuit_breaker = Mock(spec=CircuitBreaker)
        handler = ExecutionHandler(state_manager, circuit_breaker)
        
        error = ValueError("test error")
        
        # Act
        from unittest.mock import patch
        with patch('core.error_registry.ErrorRegistry') as mock_registry:
            handler.handle_general_error(
                "test.pdf", error, register_error=False
            )
            
            # Assert
            mock_registry.return_value.register.assert_not_called()

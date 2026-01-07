
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from core.client import LLMClientFactory, OllamaHealthCheck

def test_ollama_integration():
    print("Testing Ollama Integration...")
    
    # 1. Health Check
    base_url = "http://localhost:11434/v1"
    is_up = OllamaHealthCheck.is_available(base_url)
    print(f"Ollama Health ({base_url}): {'UP' if is_up else 'DOWN (Expected if not running)'}")
    
    # 2. Factory Creation
    try:
        client = LLMClientFactory.create(provider="ollama")
        print("Factory created Sync client: OK")
        print(f"Client base_url: {client.client.base_url}")
    except Exception as e:
        print(f"Factory Sync failed: {e}")
        
    try:
        async_client = LLMClientFactory.create_async(provider="ollama")
        print("Factory created Async client: OK")
    except Exception as e:
        print(f"Factory Async failed: {e}")

    # 3. Test Auto-Restart (Mocked)
    if "--restart-test" in sys.argv:
        print("\n--- Testing Auto-Restart Logic (Mocked) ---")
        from unittest.mock import patch, MagicMock
        
        # We want to simulate:
        # 1. First health check fails (triggering restart)
        # 2. restart_service returns True
        # 3. Subsequent health checks pass
        
        print("Mocking OllamaHealthCheck to simulate downtime...")
        
        with patch("core.client.OllamaHealthCheck.is_available", side_effect=[False, False, True]) as mock_is_avail, \
             patch("core.client.OllamaHealthCheck.restart_service", return_value=True) as mock_restart:
            
            print("Attempting to create client...")
            try:
                client = LLMClientFactory.create(provider="ollama")
                print("Client creation returned successfully.")
                
                # Check if restart was called
                if mock_restart.called:
                    print("SUCCESS: restart_service() was triggered.")
                else:
                    print("FAILURE: restart_service() was NOT triggered.")
                    
            except Exception as e:
                print(f"FAILURE: Exception during mocked flow: {e}")

if __name__ == "__main__":
    test_ollama_integration()

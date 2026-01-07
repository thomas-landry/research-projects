
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

if __name__ == "__main__":
    test_ollama_integration()

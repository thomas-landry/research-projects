"""
Platform Utilities.
Handles platform-specific service control (e.g., restarting Ollama).
"""
import requests
import subprocess
import platform
import time
from core.utils import get_logger
from core.config import settings

logger = get_logger("PlatformUtils")

class OllamaServiceManager:
    """Checks availability of local Ollama instance and manages restart."""
    
    @staticmethod
    def is_available(base_url: str) -> bool:
        """Check if Ollama API is responsive."""
        try:
            # Simple check to /api/tags or version
            # Only checking connectivity here
            url = base_url.replace("/v1", "") # standard ollama api is at root/api
            if not url.endswith("/"):
                url += "/"
            
            # Check version
            resp = requests.get(
                f"{url}api/version", 
                timeout=settings.OLLAMA_HEALTH_CHECK_TIMEOUT
            )
            return resp.status_code == 200
        except requests.Timeout as e:
            logger.debug(f"Ollama health check timeout after {settings.OLLAMA_HEALTH_CHECK_TIMEOUT}s: {e}")
            return False
        except requests.ConnectionError as e:
            logger.debug(f"Ollama health check connection failed: {e}")
            return False
        except requests.RequestException as e:
            logger.warning(f"Ollama health check failed with unexpected error: {e}", exc_info=True)
            return False

    @staticmethod
    def restart_service() -> bool:
        """
        Attempt to restart the Ollama service.
        Returns True if restart appears successful (process launched).
        """
        logger.info("Attempting to auto-restart Ollama service...")

        # 1. Kill existing if any (Unix/Mac specific)
        if platform.system() != "Windows":
             try:
                 subprocess.run(["pkill", "ollama"], check=False)
                 time.sleep(settings.PROCESS_KILL_GRACE_PERIOD)
             except Exception as e:
                 logger.warning(f"Could not kill existing ollama process: {e}")

        # 2. Start new instance
        try:
            # Run in background
            # Check for brew services first on Mac
            if platform.system() == "Darwin":
                # Try brew services restart first as it's cleaner
                res = subprocess.run(
                    ["brew", "services", "restart", "ollama"], 
                    capture_output=True
                )
                if res.returncode == 0:
                    logger.info("Restarted via brew services")
                    return True
            
            # Fallback to direct execution
            subprocess.Popen(
                ["ollama", "serve"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            logger.info("Launched 'ollama serve' subprocess")
            return True
        except FileNotFoundError:
            logger.error("Could not find 'ollama' executable in PATH")
            return False
        except Exception as e:
            logger.error(f"Failed to restart ollama: {e}")
            return False

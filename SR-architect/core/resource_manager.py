
import psutil
from enum import Enum
from core.utils import get_logger

logger = get_logger("ResourceManager")

class ResourceStatus(Enum):
    NORMAL = "normal"
    THROTTLE = "throttle"
    CRITICAL = "critical"

class ResourceManager:
    """
    Monitors system resources (RAM, CPU) to manage local inference load.
    Targeting M4 Macbook Pro (24GB).
    """
    def __init__(self, ram_ceiling_gb: float = 18.0, ram_throttle_gb: float = 14.0):
        self.ram_ceiling_gb = ram_ceiling_gb
        self.ram_throttle_gb = ram_throttle_gb
        
    def check_status(self) -> ResourceStatus:
        """Check current RAM usage against thresholds."""
        try:
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024 ** 3)
            
            if used_gb > self.ram_ceiling_gb:
                logger.warning(f"RAM Critical: {used_gb:.1f}GB > {self.ram_ceiling_gb}GB")
                return ResourceStatus.CRITICAL
            elif used_gb > self.ram_throttle_gb:
                logger.warning(f"RAM Throttle: {used_gb:.1f}GB > {self.ram_throttle_gb}GB")
                return ResourceStatus.THROTTLE
            else:
                return ResourceStatus.NORMAL
        except Exception as e:
            logger.error(f"Failed to check resources: {e}")
            return ResourceStatus.NORMAL # Fail open if monitoring fails
            
    def get_recommended_workers(self, max_workers: int = 6) -> int:
        """Get recommended worker count based on system status."""
        status = self.check_status()
        
        if status == ResourceStatus.NORMAL:
            return max_workers
        elif status == ResourceStatus.THROTTLE:
            return max(1, max_workers // 2)
        else: # CRITICAL
            return 1

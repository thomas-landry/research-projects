
import pytest
from unittest.mock import patch, MagicMock

def test_resource_manager_init():
    try:
        from core.resource_manager import ResourceManager
    except ImportError:
        pytest.fail("Could not import ResourceManager")
        
    rm = ResourceManager(ram_ceiling_gb=18.0, ram_throttle_gb=14.0)
    assert rm.ram_ceiling_gb == 18.0

def test_resource_status_normal():
    from core.resource_manager import ResourceManager, ResourceStatus
    
    with patch("psutil.virtual_memory") as mock_mem:
        # Mock 10GB used (below 14GB throttle)
        mock_mem.return_value.used = 10 * 1024**3
        mock_mem.return_value.percent = 40.0
        
        rm = ResourceManager(ram_ceiling_gb=18.0, ram_throttle_gb=14.0)
        status = rm.check_status()
        
        assert status == ResourceStatus.NORMAL

def test_resource_status_throttle():
    from core.resource_manager import ResourceManager, ResourceStatus
    
    with patch("psutil.virtual_memory") as mock_mem:
        # Mock 15GB used (above 14GB throttle)
        mock_mem.return_value.used = 15 * 1024**3
        mock_mem.return_value.percent = 60.0
        
        rm = ResourceManager(ram_ceiling_gb=18.0, ram_throttle_gb=14.0)
        status = rm.check_status()
        
        assert status == ResourceStatus.THROTTLE

def test_resource_status_critical():
    from core.resource_manager import ResourceManager, ResourceStatus
    
    with patch("psutil.virtual_memory") as mock_mem:
        # Mock 19GB used (above 18GB ceiling)
        mock_mem.return_value.used = 19 * 1024**3
        mock_mem.return_value.percent = 80.0
        
        rm = ResourceManager(ram_ceiling_gb=18.0, ram_throttle_gb=14.0)
        status = rm.check_status()
        
        assert status == ResourceStatus.CRITICAL

def test_get_recommended_workers():
    from core.resource_manager import ResourceManager, ResourceStatus
    
    # Normal -> Default workers (e.g. 6)
    with patch("core.resource_manager.ResourceManager.check_status", return_value=ResourceStatus.NORMAL):
        rm = ResourceManager()
        assert rm.get_recommended_workers(max_workers=6) == 6
        
    # Throttle -> Reduced (e.g. 50%)
    with patch("core.resource_manager.ResourceManager.check_status", return_value=ResourceStatus.THROTTLE):
        rm = ResourceManager()
        workers = rm.get_recommended_workers(max_workers=6)
        assert workers < 6
        assert workers >= 1
        
    # Critical -> Min (1)
    with patch("core.resource_manager.ResourceManager.check_status", return_value=ResourceStatus.CRITICAL):
        rm = ResourceManager()
        assert rm.get_recommended_workers(max_workers=6) == 1

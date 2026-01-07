
import logging
import pytest
from core.utils import setup_logging
from core.config import settings
from pathlib import Path
import shutil

@pytest.fixture
def clean_logs():
    log_dir = Path("logs_test_levels")
    if log_dir.exists():
        shutil.rmtree(log_dir)
    yield log_dir
    if log_dir.exists():
        shutil.rmtree(log_dir)

def test_dual_layer_logging(clean_logs):
    log_file = clean_logs / "test.log"
    
    # We expect: Console -> INFO, File -> DEBUG
    # But we might want to allow overriding console level via verbose flag.
    # The requirement says "clean console output", implying default should be INFO.
    
    setup_logging(level="INFO", log_file=log_file) # Calling with default/INFO intention for console
    
    root_logger = logging.getLogger()
    
    # Root logger should be DEBUG to allow file handler to catch debug logs
    # wait, if I pass level="INFO" to setup_logging, current implementation sets root to INFO.
    # I need to change how setup_logging works.
    
    # Let's check handlers
    console_handler = None
    file_handler = None
    
    for h in root_logger.handlers:
        if "RichHandler" in str(type(h)):
            console_handler = h
        elif "FileHandler" in str(type(h)):
            file_handler = h
            
    assert console_handler is not None
    assert file_handler is not None
    
    # In the new implementation, we want:
    # Console Handler Level >= INFO
    # File Handler Level == DEBUG
    # Root Logger Level == DEBUG (to propagate everything to handlers)
    
    assert root_logger.level == logging.DEBUG
    assert console_handler.level == logging.INFO
    assert file_handler.level == logging.DEBUG


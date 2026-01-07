
import pytest
from core.audit_logger import AuditLogger
import json

def test_failure_taxonomy_logging(tmp_path):
    log_dir = tmp_path / "logs"
    logger = AuditLogger(log_dir=str(log_dir), session_name="test")
    
    # Log an error with a specific failure type
    # This assumes we update the API to accept failure_type
    try:
        logger.log_extraction(
            filename="test.pdf",
            status="error",
            error_message="Out of memory",
            failure_type="oom" # New arg
        )
    except TypeError:
        pytest.fail("log_extraction does not accept failure_type")
        
    # Verify it's stored
    entry = logger.entries[0]
    assert entry.status == "error"
    assert getattr(entry, "failure_type", None) == "oom"
    
    # Verify JSON
    with open(logger.log_file, "r") as f:
        data = json.loads(f.read())
        assert data["failure_type"] == "oom"

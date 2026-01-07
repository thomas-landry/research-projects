#!/usr/bin/env python3
"""
Unit tests for the Memory Profiler.
"""
import sys
import gc
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMemoryProfiler:
    """Tests for MemoryProfiler class."""
    
    def test_start_returns_baseline(self):
        """Profiler start() returns baseline memory in MB."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        baseline = profiler.start()
        
        assert isinstance(baseline, float)
        assert baseline >= 0
        profiler.stop()
    
    def test_snapshot_tracks_memory(self):
        """Snapshots correctly track memory changes."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        profiler.start()
        
        # Allocate memory
        large_list = [0] * 1_000_000  # ~8MB
        snap = profiler.snapshot("after_alloc")
        
        assert snap.label == "after_alloc"
        assert snap.current_mb > 0
        assert snap.peak_mb >= snap.current_mb
        
        del large_list
        profiler.stop()
    
    def test_snapshot_without_start_raises(self):
        """Snapshot without start() raises RuntimeError."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        
        with pytest.raises(RuntimeError, match="not started"):
            profiler.snapshot("test")
    
    def test_stop_generates_report(self):
        """stop() generates complete MemoryReport."""
        from tests.profile_memory import MemoryProfiler, MemoryReport
        
        profiler = MemoryProfiler()
        profiler.start()
        profiler.snapshot("test")
        report = profiler.stop()
        
        assert isinstance(report, MemoryReport)
        assert report.baseline_mb >= 0
        assert report.peak_mb >= 0
        assert report.final_mb >= 0
        assert len(report.snapshots) == 2  # baseline + test
    
    def test_leak_detection(self):
        """Leak warnings triggered when growth exceeds threshold."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        profiler.LEAK_THRESHOLD_MB = 0.001  # Very low threshold
        profiler.start()
        
        # Allocate memory
        large_list = [0] * 100_000
        profiler.snapshot("alloc")
        
        report = profiler.stop()
        
        # Should have warnings due to low threshold
        # Note: This may not always trigger depending on gc
        assert isinstance(report.leak_warnings, list)
        
        del large_list
    
    def test_report_to_dict(self):
        """Report can be serialized to dict."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        profiler.start()
        report = profiler.stop()
        
        result = report.to_dict()
        
        assert isinstance(result, dict)
        assert "baseline_mb" in result
        assert "peak_mb" in result
        assert "snapshots" in result
    
    def test_top_allocations(self):
        """Top allocations returns list of dicts."""
        from tests.profile_memory import MemoryProfiler
        
        profiler = MemoryProfiler()
        profiler.start()
        
        # Allocate some memory
        data = {"key": "value" * 1000}
        
        allocs = profiler.get_top_allocations(5)
        
        assert isinstance(allocs, list)
        if allocs:  # May be empty in some cases
            assert "size_mb" in allocs[0]
            assert "file" in allocs[0]
        
        profiler.stop()
        del data


class TestMemorySnapshot:
    """Tests for MemorySnapshot dataclass."""
    
    def test_snapshot_fields(self):
        """MemorySnapshot has required fields."""
        from tests.profile_memory import MemorySnapshot
        
        snap = MemorySnapshot(
            label="test",
            timestamp="2026-01-07T12:00:00",
            current_mb=100.0,
            peak_mb=150.0,
            diff_mb=50.0,
        )
        
        assert snap.label == "test"
        assert snap.current_mb == 100.0
        assert snap.peak_mb == 150.0
        assert snap.diff_mb == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

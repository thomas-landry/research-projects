#!/usr/bin/env python3
"""
Memory Profiler for SR-Architect Pipeline.

Uses tracemalloc to measure memory usage during extraction operations.
Provides baseline snapshots, peak tracking, and leak detection.
"""
import sys
import gc
import json
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class MemorySnapshot:
    """Single memory measurement."""
    label: str
    timestamp: str
    current_mb: float
    peak_mb: float
    diff_mb: float = 0.0


@dataclass  
class MemoryReport:
    """Complete memory profiling report."""
    start_time: str
    end_time: str
    baseline_mb: float
    peak_mb: float
    final_mb: float
    growth_mb: float
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    top_allocations: List[Dict[str, Any]] = field(default_factory=list)
    leak_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "baseline_mb": self.baseline_mb,
            "peak_mb": self.peak_mb,
            "final_mb": self.final_mb,
            "growth_mb": self.growth_mb,
            "snapshots": [asdict(s) for s in self.snapshots],
            "top_allocations": self.top_allocations,
            "leak_warnings": self.leak_warnings,
        }


class MemoryProfiler:
    """
    Profile memory usage of SR-Architect operations.
    
    Usage:
        profiler = MemoryProfiler()
        profiler.start()
        profiler.snapshot("before_parse")
        # ... do work ...
        profiler.snapshot("after_parse")
        report = profiler.stop()
    """
    
    # Threshold for leak warning (MB)
    LEAK_THRESHOLD_MB = 50.0
    # Maximum acceptable peak (MB)
    MAX_PEAK_MB = 2000.0
    
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.start_time: Optional[str] = None
        self.baseline_mb: float = 0.0
        self._started = False
        
    def start(self) -> float:
        """Start memory tracking. Returns baseline memory in MB."""
        gc.collect()  # Clean slate
        tracemalloc.start()
        
        self.start_time = datetime.now().isoformat()
        current, peak = tracemalloc.get_traced_memory()
        self.baseline_mb = current / (1024 * 1024)
        self._started = True
        
        self.snapshots = [MemorySnapshot(
            label="baseline",
            timestamp=self.start_time,
            current_mb=self.baseline_mb,
            peak_mb=peak / (1024 * 1024),
        )]
        
        return self.baseline_mb
    
    def snapshot(self, label: str) -> MemorySnapshot:
        """Take a memory snapshot with given label."""
        if not self._started:
            raise RuntimeError("Profiler not started. Call start() first.")
            
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        
        prev_mb = self.snapshots[-1].current_mb if self.snapshots else 0
        
        snap = MemorySnapshot(
            label=label,
            timestamp=datetime.now().isoformat(),
            current_mb=current_mb,
            peak_mb=peak_mb,
            diff_mb=current_mb - prev_mb,
        )
        self.snapshots.append(snap)
        return snap
    
    def get_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory-consuming code locations."""
        if not self._started:
            return []
            
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:limit]
        
        return [
            {
                "file": str(stat.traceback),
                "size_mb": stat.size / (1024 * 1024),
                "count": stat.count,
            }
            for stat in top_stats
        ]
    
    def stop(self) -> MemoryReport:
        """Stop tracking and generate report."""
        if not self._started:
            raise RuntimeError("Profiler not started.")
            
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        final_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        
        # Get top allocations before stopping
        top_allocs = self.get_top_allocations()
        
        tracemalloc.stop()
        self._started = False
        
        end_time = datetime.now().isoformat()
        growth_mb = final_mb - self.baseline_mb
        
        # Detect potential leaks
        leak_warnings = []
        if growth_mb > self.LEAK_THRESHOLD_MB:
            leak_warnings.append(
                f"Memory grew by {growth_mb:.1f}MB (threshold: {self.LEAK_THRESHOLD_MB}MB)"
            )
        if peak_mb > self.MAX_PEAK_MB:
            leak_warnings.append(
                f"Peak memory {peak_mb:.1f}MB exceeds limit ({self.MAX_PEAK_MB}MB)"
            )
            
        return MemoryReport(
            start_time=self.start_time,
            end_time=end_time,
            baseline_mb=self.baseline_mb,
            peak_mb=peak_mb,
            final_mb=final_mb,
            growth_mb=growth_mb,
            snapshots=self.snapshots,
            top_allocations=top_allocs,
            leak_warnings=leak_warnings,
        )


def profile_extraction_pipeline(papers_dir: str, limit: int = 3) -> MemoryReport:
    """
    Profile the full extraction pipeline.
    
    Args:
        papers_dir: Directory containing PDFs
        limit: Number of papers to process
        
    Returns:
        MemoryReport with profiling results
    """
    from core.parser import DocumentParser
    from core.content_filter import ContentFilter
    from core.hierarchical_pipeline import HierarchicalExtractionPipeline
    from core.schema_builder import get_case_report_schema, build_extraction_model
    
    profiler = MemoryProfiler()
    profiler.start()
    
    # Phase 1: Parser initialization
    parser = DocumentParser()
    profiler.snapshot("parser_init")
    
    # Phase 2: Parse PDFs
    papers_path = Path(papers_dir)
    pdf_files = list(papers_path.glob("*.pdf"))[:limit]
    
    parsed_docs = []
    for pdf in pdf_files:
        doc = parser.parse_pdf(str(pdf))
        parsed_docs.append(doc)
        profiler.snapshot(f"parsed_{pdf.stem[:20]}")
    
    # Phase 3: Pipeline initialization
    pipeline = HierarchicalExtractionPipeline(
        provider="ollama",
        model="llama3.1:8b",
    )
    profiler.snapshot("pipeline_init")
    
    # Phase 4: Content filtering
    content_filter = ContentFilter()
    for doc in parsed_docs:
        content_filter.filter_chunks(doc.chunks)
    profiler.snapshot("content_filtered")
    
    # Phase 5: Cleanup
    del parsed_docs
    del parser
    del pipeline
    del content_filter
    gc.collect()
    profiler.snapshot("after_cleanup")
    
    return profiler.stop()


def main():
    """Run memory profiling and generate report."""
    print("=" * 60)
    print("SR-Architect Memory Profiler")
    print("=" * 60)
    
    base_dir = Path(__file__).parent.parent
    papers_dir = base_dir / "papers_benchmark"
    output_dir = base_dir / "tests" / "output" / "memory_profile"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nProfiling extraction on: {papers_dir}")
    print(f"Output: {output_dir}\n")
    
    report = profile_extraction_pipeline(str(papers_dir), limit=3)
    
    # Print summary
    print("\n" + "=" * 60)
    print("MEMORY PROFILE RESULTS")
    print("=" * 60)
    print(f"\nBaseline: {report.baseline_mb:.1f} MB")
    print(f"Peak:     {report.peak_mb:.1f} MB")
    print(f"Final:    {report.final_mb:.1f} MB")
    print(f"Growth:   {report.growth_mb:.1f} MB")
    
    print("\nSnapshots:")
    for snap in report.snapshots:
        diff = f"+{snap.diff_mb:.1f}" if snap.diff_mb >= 0 else f"{snap.diff_mb:.1f}"
        print(f"  {snap.label:30} {snap.current_mb:8.1f} MB ({diff} MB)")
    
    if report.leak_warnings:
        print("\n⚠️  WARNINGS:")
        for warning in report.leak_warnings:
            print(f"  - {warning}")
    
    print("\nTop Memory Allocations:")
    for i, alloc in enumerate(report.top_allocations[:5], 1):
        print(f"  {i}. {alloc['size_mb']:.2f} MB - {alloc['file'][:60]}")
    
    # Save report
    report_path = output_dir / "memory_report.json"
    with open(report_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"\n✓ Report saved: {report_path}")
    
    # Return exit code based on thresholds
    if report.peak_mb > MemoryProfiler.MAX_PEAK_MB:
        print(f"\n❌ FAIL: Peak memory exceeds {MemoryProfiler.MAX_PEAK_MB}MB")
        return 1
    
    print("\n✓ Memory profile within acceptable limits")
    return 0


if __name__ == "__main__":
    sys.exit(main())

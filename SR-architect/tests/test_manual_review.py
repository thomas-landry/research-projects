"""
Tests for ManualReviewQueue.
Validates SQLite storage and queue operations.
"""
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

from core.manual_review import ManualReviewQueue, ReviewItem, ReviewStatus


class TestManualReviewQueue(unittest.TestCase):
    """Tests for ManualReviewQueue SQLite operations."""
    
    def setUp(self):
        # Use temp file for test DB
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_review.db"
        self.queue = ManualReviewQueue(db_path=self.db_path)
        
    def tearDown(self):
        self.queue.close()
        if self.db_path.exists():
            self.db_path.unlink()
            
    def test_add_item(self):
        """Test adding an item to the queue."""
        item_id = self.queue.add(
            paper_path="/papers/test.pdf",
            failure_reason="All tiers failed",
            field_name="sample_size",
        )
        
        self.assertIsNotNone(item_id)
        self.assertGreater(item_id, 0)
        
    def test_get_item(self):
        """Test retrieving an item by ID."""
        item_id = self.queue.add(
            paper_path="/papers/test.pdf",
            failure_reason="Low confidence"
        )
        
        item = self.queue.get(item_id)
        
        self.assertIsNotNone(item)
        self.assertEqual(item.paper_path, "/papers/test.pdf")
        self.assertEqual(item.failure_reason, "Low confidence")
        self.assertEqual(item.status, ReviewStatus.PENDING)
        
    def test_list_pending(self):
        """Test listing pending items."""
        self.queue.add(paper_path="/papers/a.pdf", failure_reason="Tier 2 failed")
        self.queue.add(paper_path="/papers/b.pdf", failure_reason="Tier 3 failed")
        
        pending = self.queue.list_pending()
        
        self.assertEqual(len(pending), 2)
        
    def test_resolve_item(self):
        """Test resolving a review item."""
        item_id = self.queue.add(
            paper_path="/papers/test.pdf",
            failure_reason="Extraction failed"
        )
        
        self.queue.resolve(
            item_id=item_id,
            resolution="Manual extraction completed",
            resolved_value="150"
        )
        
        item = self.queue.get(item_id)
        self.assertEqual(item.status, ReviewStatus.RESOLVED)
        self.assertEqual(item.resolved_value, "150")
        
    def test_skip_item(self):
        """Test skipping a review item."""
        item_id = self.queue.add(
            paper_path="/papers/test.pdf",
            failure_reason="Cannot parse"
        )
        
        self.queue.skip(item_id, reason="Paper not relevant")
        
        item = self.queue.get(item_id)
        self.assertEqual(item.status, ReviewStatus.SKIPPED)
        
    def test_count_by_status(self):
        """Test counting items by status."""
        self.queue.add(paper_path="/papers/a.pdf", failure_reason="Test")
        self.queue.add(paper_path="/papers/b.pdf", failure_reason="Test")
        item_id = self.queue.add(paper_path="/papers/c.pdf", failure_reason="Test")
        self.queue.resolve(item_id, "Done", "100")
        
        counts = self.queue.get_counts()
        
        self.assertEqual(counts["pending"], 2)
        self.assertEqual(counts["resolved"], 1)
        
    def test_export_pending(self):
        """Test exporting pending items to dict format."""
        self.queue.add(paper_path="/papers/test.pdf", failure_reason="Test", field_name="age")
        
        export = self.queue.export_pending()
        
        self.assertEqual(len(export), 1)
        self.assertEqual(export[0]["paper_path"], "/papers/test.pdf")
        self.assertEqual(export[0]["field_name"], "age")


if __name__ == "__main__":
    unittest.main()

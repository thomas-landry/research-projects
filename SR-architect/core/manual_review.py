"""
Manual Review Queue for papers where extraction fails.

Stores failed papers in SQLite for later manual review.
Provides CLI-accessible operations: list, export, resolve, skip.

Per plan.md: Store failure reason, provide CLI commands.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json

from core.utils import get_logger

logger = get_logger("ManualReview")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / ".cache" / "manual_review.db"


class ReviewStatus(Enum):
    """Status of a review item."""
    PENDING = "pending"
    RESOLVED = "resolved"
    SKIPPED = "skipped"


@dataclass
class ReviewItem:
    """A single item in the manual review queue."""
    id: int
    paper_path: str
    failure_reason: str
    field_name: Optional[str]
    status: ReviewStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    resolved_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ManualReviewQueue:
    """
    SQLite-backed queue for papers needing manual review.
    
    Use when:
    - All extraction tiers fail
    - Self-consistency voting fails
    - Validation rules catch anomalies
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS review_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_path TEXT NOT NULL,
        failure_reason TEXT NOT NULL,
        field_name TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution TEXT,
        resolved_value TEXT,
        metadata TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_status ON review_queue(status);
    CREATE INDEX IF NOT EXISTS idx_paper ON review_queue(paper_path);
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the review queue.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        
        logger.debug(f"ManualReviewQueue initialized at {self.db_path}")
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()
    
    def add(
        self,
        paper_path: str,
        failure_reason: str,
        field_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add a paper to the review queue.
        
        Args:
            paper_path: Path to the PDF file
            failure_reason: Why extraction failed
            field_name: Specific field that failed (optional)
            metadata: Additional context (optional)
            
        Returns:
            ID of the created queue item
        """
        cursor = self._conn.execute(
            """
            INSERT INTO review_queue (paper_path, failure_reason, field_name, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (paper_path, failure_reason, field_name, json.dumps(metadata) if metadata else None)
        )
        self._conn.commit()
        
        item_id = cursor.lastrowid
        logger.info(f"Added to review queue: {Path(paper_path).name} (id={item_id})")
        return item_id
    
    def get(self, item_id: int) -> Optional[ReviewItem]:
        """Get a single review item by ID."""
        row = self._conn.execute(
            "SELECT * FROM review_queue WHERE id = ?", (item_id,)
        ).fetchone()
        
        if row:
            return self._row_to_item(row)
        return None
    
    def list_pending(self, limit: int = 100) -> List[ReviewItem]:
        """List all pending review items."""
        rows = self._conn.execute(
            """
            SELECT * FROM review_queue 
            WHERE status = 'pending' 
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [self._row_to_item(row) for row in rows]
    
    def list_all(self, status: Optional[ReviewStatus] = None, limit: int = 100) -> List[ReviewItem]:
        """List all review items, optionally filtered by status."""
        if status:
            rows = self._conn.execute(
                "SELECT * FROM review_queue WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM review_queue ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        
        return [self._row_to_item(row) for row in rows]
    
    def resolve(
        self,
        item_id: int,
        resolution: str,
        resolved_value: Optional[str] = None,
    ):
        """
        Mark an item as resolved.
        
        Args:
            item_id: Queue item ID
            resolution: How it was resolved
            resolved_value: Manually extracted value (optional)
        """
        self._conn.execute(
            """
            UPDATE review_queue 
            SET status = 'resolved', resolution = ?, resolved_value = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (resolution, resolved_value, item_id)
        )
        self._conn.commit()
        logger.info(f"Resolved review item {item_id}")
    
    def skip(self, item_id: int, reason: str = "Skipped by user"):
        """Mark an item as skipped."""
        self._conn.execute(
            """
            UPDATE review_queue 
            SET status = 'skipped', resolution = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reason, item_id)
        )
        self._conn.commit()
        logger.info(f"Skipped review item {item_id}: {reason}")
    
    def get_counts(self) -> Dict[str, int]:
        """Get count of items by status."""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as count FROM review_queue GROUP BY status"
        ).fetchall()
        
        counts = {"pending": 0, "resolved": 0, "skipped": 0}
        for row in rows:
            counts[row["status"]] = row["count"]
        
        return counts
    
    def export_pending(self) -> List[Dict[str, Any]]:
        """Export pending items as list of dicts (for CLI/JSON output)."""
        items = self.list_pending()
        return [
            {
                "id": item.id,
                "paper_path": item.paper_path,
                "failure_reason": item.failure_reason,
                "field_name": item.field_name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    
    def _row_to_item(self, row: sqlite3.Row) -> ReviewItem:
        """Convert a database row to ReviewItem."""
        return ReviewItem(
            id=row["id"],
            paper_path=row["paper_path"],
            failure_reason=row["failure_reason"],
            field_name=row["field_name"],
            status=ReviewStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            resolution=row["resolution"],
            resolved_value=row["resolved_value"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )
    
    def close(self):
        """Close the database connection."""
        self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, _exc_type, _exc_val, _traceback):
        self.close()

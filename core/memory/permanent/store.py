"""
Permanent Memory: Store Department

SQLite-backed persistent storage with tags.
Thread-safe via sqlite3 check_same_thread + module-level lock.
"""

import json
import sqlite3
import threading
from pathlib import Path

from runtime.config.config import MEMORY
from core.memory.permanent.intake import PermanentEntry

_lock = threading.Lock()
_DB_INITIALIZED = False


def _get_db_path() -> Path:
    return Path(MEMORY["permanent_db"])


def _init_db(conn: sqlite3.Connection) -> None:
    """Create the permanent memory table if it doesn't exist."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS permanent_memory (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            keywords TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_accessed REAL NOT NULL,
            access_count INTEGER DEFAULT 0,
            source TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_permanent_tags
        ON permanent_memory(tags)
    """)
    conn.commit()
    _DB_INITIALIZED = True


def _connect() -> sqlite3.Connection:
    """Open a connection and ensure table exists."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _row_to_entry(row: sqlite3.Row) -> PermanentEntry:
    return PermanentEntry(
        id=row["id"],
        content=row["content"],
        keywords=json.loads(row["keywords"]),
        tags=json.loads(row["tags"]),
        created_at=row["created_at"],
        last_accessed=row["last_accessed"],
        access_count=row["access_count"],
        source=row["source"],
        metadata=json.loads(row["metadata"]),
    )


def save_entry(entry: PermanentEntry) -> None:
    """Insert a new permanent entry."""
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO permanent_memory
                   (id, content, keywords, tags, created_at,
                    last_accessed, access_count, source, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.content,
                    json.dumps(entry.keywords),
                    json.dumps(entry.tags),
                    entry.created_at,
                    entry.last_accessed,
                    entry.access_count,
                    entry.source,
                    json.dumps(entry.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def load_all() -> list[PermanentEntry]:
    """Load all permanent entries."""
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM permanent_memory ORDER BY created_at DESC"
            ).fetchall()
            return [_row_to_entry(r) for r in rows]
        finally:
            conn.close()


def update_entry(entry: PermanentEntry) -> bool:
    """Update an existing entry."""
    with _lock:
        conn = _connect()
        try:
            cursor = conn.execute(
                """UPDATE permanent_memory SET
                   content=?, keywords=?, tags=?, last_accessed=?,
                   access_count=?, source=?, metadata=?
                   WHERE id=?""",
                (
                    entry.content,
                    json.dumps(entry.keywords),
                    json.dumps(entry.tags),
                    entry.last_accessed,
                    entry.access_count,
                    entry.source,
                    json.dumps(entry.metadata),
                    entry.id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def delete_entry(entry_id: str, user_confirmed: bool = False) -> bool:
    """
    Delete a permanent entry. REQUIRES user_confirmed=True.
    The Guard department enforces this.
    """
    if not user_confirmed:
        return False

    with _lock:
        conn = _connect()
        try:
            cursor = conn.execute(
                "DELETE FROM permanent_memory WHERE id=?", (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def count() -> int:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM permanent_memory"
            ).fetchone()
            return row["cnt"]
        finally:
            conn.close()

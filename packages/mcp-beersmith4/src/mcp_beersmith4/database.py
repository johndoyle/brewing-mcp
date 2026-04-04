"""SQLite connection management for BeerSmith 4 databases.

Provides read-only access by default with optional write support
gated behind explicit configuration and safety checks.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from mcp_beersmith4.config import BeerSmith4Config


class SchemaFingerprint:
    """Tracks database schema to detect drift from BeerSmith updates."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._fingerprint: str | None = None

    def capture(self) -> str:
        """Capture current schema fingerprint."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        try:
            cur = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            schema_text = "\n".join(row[0] for row in cur if row[0])
            self._fingerprint = hashlib.sha256(schema_text.encode()).hexdigest()[:16]
            return self._fingerprint
        finally:
            conn.close()

    def verify(self) -> bool:
        """Return True if schema matches the previously captured fingerprint."""
        if self._fingerprint is None:
            return True
        return self.capture() == self._fingerprint


class DatabaseManager:
    """Manages SQLite connections to BeerSmith 4 databases."""

    def __init__(self, config: BeerSmith4Config):
        self._config = config
        self._schema_fp = SchemaFingerprint(config.main_db)
        self._schema_fp.capture()

    @contextmanager
    def read_connection(
        self, db_path: Path | None = None
    ) -> Generator[sqlite3.Connection, None, None]:
        """Open a read-only connection to the specified database.

        Args:
            db_path: Database file path. Defaults to BeerSmith.sqlite.
        """
        path = db_path or self._config.main_db
        if not path.exists():
            raise FileNotFoundError(f"Database not found: {path}")

        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def write_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a writable connection with safety checks.

        Raises:
            PermissionError: If config is read-only.
            RuntimeError: If schema has drifted since startup.
        """
        if self._config.read_only:
            raise PermissionError(
                "Write access disabled. Set BEERSMITH4_READ_ONLY=false to enable."
            )

        if not self._schema_fp.verify():
            raise RuntimeError(
                "Database schema has changed since server startup. "
                "Restart the server to re-validate before writing."
            )

        conn = sqlite3.connect(str(self._config.main_db))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_backup(self) -> Path:
        """Create a snapshot backup of the main database before writes.

        Returns:
            Path to the backup file.
        """
        backup_dir = self._config.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        dest = backup_dir / f"BeerSmith4-mcp-backup-{ts}.sqlite"
        shutil.copy2(self._config.main_db, dest)
        return dest

    def query(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
        db_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only query and return rows as dicts."""
        with self.read_connection(db_path) as conn:
            cur = conn.execute(sql, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def query_one(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
        db_path: Path | None = None,
    ) -> dict[str, Any] | None:
        """Execute a read-only query and return the first row as a dict."""
        rows = self.query(sql, params, db_path)
        return rows[0] if rows else None

    def execute_write(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> int:
        """Execute a write query. Returns lastrowid."""
        with self.write_connection() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid or 0

    def next_permid(self, table: str) -> int:
        """Get the next available _PERMID_ for a table."""
        row = self.query_one(f"SELECT MAX(_PERMID_) as m FROM [{table}]")  # noqa: S608
        return (row["m"] or 0) + 1 if row else 1

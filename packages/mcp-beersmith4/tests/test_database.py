"""Tests for DatabaseManager."""

from __future__ import annotations

import pytest

from mcp_beersmith4.config import BeerSmith4Config
from mcp_beersmith4.database import DatabaseManager


class TestDatabaseManager:
    def test_query_grains(self, db: DatabaseManager):
        rows = db.query("SELECT * FROM M_GRAIN ORDER BY F_G_NAME")
        assert len(rows) == 3
        assert rows[0]["F_G_NAME"] == "Crystal 60L"

    def test_query_one(self, db: DatabaseManager):
        row = db.query_one("SELECT * FROM M_GRAIN WHERE _PERMID_ = ?", (1,))
        assert row is not None
        assert row["F_G_NAME"] == "Pale Malt (2 Row) US"

    def test_query_one_not_found(self, db: DatabaseManager):
        row = db.query_one("SELECT * FROM M_GRAIN WHERE _PERMID_ = ?", (999,))
        assert row is None

    def test_next_permid(self, db: DatabaseManager):
        nxt = db.next_permid("M_GRAIN")
        assert nxt == 4  # 3 seeded grains

    def test_read_only_blocks_write(self, ro_config: BeerSmith4Config):
        db = DatabaseManager(ro_config)
        with pytest.raises(PermissionError, match="Write access disabled"):
            with db.write_connection():
                pass

    def test_write_connection(self, db: DatabaseManager):
        with db.write_connection() as conn:
            conn.execute(
                "INSERT INTO M_GRAIN (_PERMID_, F_G_NAME) VALUES (99, 'Test Grain')"
            )
        row = db.query_one("SELECT * FROM M_GRAIN WHERE _PERMID_ = ?", (99,))
        assert row is not None
        assert row["F_G_NAME"] == "Test Grain"

    def test_create_backup(self, db: DatabaseManager, config: BeerSmith4Config):
        backup_path = db.create_backup()
        assert backup_path.exists()
        assert backup_path.parent == config.backup_dir

    def test_schema_fingerprint_stable(self, db: DatabaseManager):
        fp1 = db._schema_fp.capture()
        fp2 = db._schema_fp.capture()
        assert fp1 == fp2
        assert db._schema_fp.verify()

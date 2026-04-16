"""
database/update_db.py
──────────────────────
Database migration runner — applied once at startup.

Migrations here handle schema changes on existing databases that
CREATE TABLE IF NOT EXISTS cannot handle (drops, renames, etc.).

PostgreSQL compatible — no SQLite-specific syntax.
"""
from database.connection import get_db_conn, db_execute


def update_database() -> None:
    """Applies all pending migrations. Safe to call multiple times."""
    _drop_group_members()


def _drop_group_members() -> None:
    """
    Drops the group_members table and its index — no longer needed.
    No-op if the table/index doesn't exist (PostgreSQL IF EXISTS is safe).
    """
    db_execute("DROP INDEX IF EXISTS idx_group_members_group")
    db_execute("DROP TABLE IF EXISTS group_members")

"""
database/update_db.py
──────────────────────
Database migration runner — applied once at startup.

Migrations here handle schema changes on existing databases that
CREATE TABLE IF NOT EXISTS cannot handle (drops, renames, etc.).
"""
from database.connection import get_db_conn


def update_database() -> None:
    """Applies all pending migrations. Safe to call multiple times."""
    _drop_group_members()


def _drop_group_members() -> None:
    """
    Drops the group_members table — no longer needed.
    No-op if the table doesn't exist.
    """
    conn = get_db_conn()
    conn.execute("DROP TABLE IF EXISTS idx_group_members_group")
    conn.execute("DROP TABLE IF EXISTS group_members")
    conn.commit()

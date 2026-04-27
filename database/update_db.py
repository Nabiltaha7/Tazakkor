"""
database/update_db.py
──────────────────────
Schema migration runner — applied once at startup after init_db().

Handles changes that CREATE TABLE IF NOT EXISTS cannot cover:
table drops, column renames, index removals, etc.

Called from main.py after create_all_tables().
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

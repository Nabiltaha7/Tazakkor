"""
database/db_scheme
───────────────────
Schema definition modules — one file per domain.

Each module exposes a single create_*_tables() function.
All modules are orchestrated by database/init_db.py in FK-safe order.

Backward-compatible entry point:
    from database.db_scheme import create_all_tables
    create_all_tables()
"""
from database.init_db import init_db


def create_all_tables() -> None:
    """Backward-compatible wrapper — delegates to init_db()."""
    init_db()

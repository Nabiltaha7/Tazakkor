"""
database/connection.py
───────────────────────
Thread-local SQLite connection pool with WAL mode and write serialization.

Rules:
  - One connection per thread (thread-local).
  - All writes go through db_write() to prevent "database is locked".
  - WAL + foreign_keys + row_factory always enabled.
"""
import os
import sqlite3
import threading
import time

from core.config import DB_NAME

_local            = threading.local()
_WRITE_LOCK       = threading.Lock()


# ══════════════════════════════════════════
# Connection management
# ══════════════════════════════════════════

def _ensure_db_dir(path: str) -> None:
    """Creates parent directories for the DB file if they don't exist."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)


def get_db_conn() -> sqlite3.Connection:
    """
    Returns a thread-local SQLite connection.
    Creates the connection (and DB file) on first call per thread.
    WAL + foreign_keys + row_factory are always enabled.
    """
    if getattr(_local, "conn", None) is None:
        _ensure_db_dir(DB_NAME)
        conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def close_db_conn() -> None:
    """Closes the current thread's connection."""
    conn = getattr(_local, "conn", None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


# ══════════════════════════════════════════
# Write serialization
# ══════════════════════════════════════════

def db_write(func, *args, max_retries: int = 3, retry_delay: float = 0.15, **kwargs):
    """
    Executes a write function with retry on 'database is locked'.
    Uses a global lock to serialize concurrent writes.

    Usage:
        db_write(lambda: conn.execute("UPDATE ..."))
        db_write(my_write_fn, arg1, arg2)
    """
    with _WRITE_LOCK:
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    print(f"[db_write] database is locked after {max_retries} attempts")
                raise

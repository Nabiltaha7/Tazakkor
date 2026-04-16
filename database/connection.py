"""
database/connection.py
───────────────────────
PostgreSQL connection layer using psycopg2 (Supabase / Render).

One thread-local connection per thread — recreated automatically if
the connection is closed or in an error state.

Public API:
  get_db_conn()   → psycopg2 connection (RealDictCursor factory)
  close_db_conn() → closes the current thread's connection
  db_write(func, *args, **kwargs) → serialized write with retry

SQL conventions:
  - Use %s for all placeholders (PostgreSQL standard)
  - Use SERIAL PRIMARY KEY instead of INTEGER PRIMARY KEY AUTOINCREMENT
  - Use EXTRACT(EPOCH FROM NOW())::INTEGER instead of strftime('%s','now')
  - Use NOW() instead of datetime('now')
  - Use INSERT ... ON CONFLICT DO NOTHING instead of INSERT OR IGNORE
  - Use INSERT ... ON CONFLICT (...) DO UPDATE SET instead of INSERT OR REPLACE
"""
import threading
import time

import psycopg2
import psycopg2.extras

from core.config import DATABASE_URL

_local      = threading.local()
_WRITE_LOCK = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════

def _new_conn():
    """Opens a new psycopg2 connection to the Supabase PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    # RealDictCursor makes rows behave like dicts — consistent with sqlite3.Row
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def get_db_conn():
    """
    Returns the thread-local PostgreSQL connection.
    Creates a new connection on first call per thread, or if the
    existing connection has been closed or entered an error state.
    """
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed:
        _local.conn = _new_conn()
    else:
        # Recover from aborted transactions automatically
        try:
            if conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                # Check if the transaction is in an error state
                if conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                    conn.rollback()
        except Exception:
            # Connection is broken — replace it
            try:
                conn.close()
            except Exception:
                pass
            _local.conn = _new_conn()
    return _local.conn


def close_db_conn() -> None:
    """Closes the current thread's connection."""
    conn = getattr(_local, "conn", None)
    if conn and not conn.closed:
        try:
            conn.close()
        except Exception:
            pass
    _local.conn = None


# ══════════════════════════════════════════════════════════════════════════════
# Convenience helpers — use these instead of conn.execute() directly
# ══════════════════════════════════════════════════════════════════════════════

def db_execute(query: str, params=None) -> None:
    """
    Execute a write statement (INSERT / UPDATE / DELETE / DDL) and commit.
    Opens a cursor, executes, commits, then closes the cursor.
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(query, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        cur.close()


def db_fetchone(query: str, params=None) -> dict | None:
    """
    Execute a SELECT and return the first row as a dict, or None.
    Does NOT commit (read-only).
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()


def db_fetchall(query: str, params=None) -> list[dict]:
    """
    Execute a SELECT and return all rows as a list of dicts.
    Does NOT commit (read-only).
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()


def db_write(func, *args, max_retries: int = 3, retry_delay: float = 0.15, **kwargs):
    """
    Executes a write function with retry on transient PostgreSQL errors
    (deadlocks, serialization failures).

    A global lock serializes concurrent writes for safety.

    Usage:
        db_write(lambda: db_execute("UPDATE ..."))
        db_write(my_write_fn, arg1, arg2)
    """
    with _WRITE_LOCK:
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err = str(e).lower()
                transient = (
                    "deadlock detected"    in err
                    or "could not serialize" in err
                    or "connection reset"    in err
                )
                if transient and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                if transient:
                    print(f"[db_write] transient error after {max_retries} attempts: {e}")
                raise

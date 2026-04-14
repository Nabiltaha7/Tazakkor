"""
database/db_scheme/groups_tables.py
─────────────────────────────────────
جداول المجموعات

Tables:
  - groups : المجموعات التي يعمل فيها البوت
"""
from database.connection import get_db_conn


def create_groups_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: groups
    # PURPOSE: يسجّل كل مجموعة تيليغرام أُضيف إليها البوت.
    #
    # COLUMNS:
    #   id               — مفتاح أساسي داخلي.
    #   group_id         — معرّف تيليغرام للمجموعة (فريد).
    #   name             — اسم المجموعة.
    #   joined_at        — Unix timestamp لوقت الانضمام.
    #   tz_offset        — إزاحة UTC بالدقائق (افتراضي: 180 = UTC+3).
    #   azkar_enabled    — 1 إذا كانت الأذكار التلقائية مفعّلة.
    #   azkar_interval   — فترة إرسال الأذكار بالدقائق.
    #   azkar_rem_*      — ساعة تذكير كل نوع أذكار (NULL = معطّل).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id           INTEGER NOT NULL UNIQUE,
        name               TEXT    NOT NULL DEFAULT 'Unknown',
        joined_at          INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        tz_offset          INTEGER NOT NULL DEFAULT 180,
        azkar_enabled      INTEGER NOT NULL DEFAULT 0,
        azkar_interval     INTEGER NOT NULL DEFAULT 15,
        azkar_rem_morning  INTEGER DEFAULT NULL,
        azkar_rem_evening  INTEGER DEFAULT NULL,
        azkar_rem_sleep    INTEGER DEFAULT NULL,
        azkar_rem_wakeup   INTEGER DEFAULT NULL
    )
    """)

    # ── Safe column migrations for existing databases ─────────────
    # Only runs ALTER TABLE if the column is missing — idempotent.
    # _add_column_if_missing(cursor, conn, "groups", "tz_offset",        "INTEGER NOT NULL DEFAULT 180")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_enabled",    "INTEGER NOT NULL DEFAULT 0")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_interval",   "INTEGER NOT NULL DEFAULT 15")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_rem_morning","INTEGER DEFAULT NULL")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_rem_evening","INTEGER DEFAULT NULL")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_rem_sleep",  "INTEGER DEFAULT NULL")
    # _add_column_if_missing(cursor, conn, "groups", "azkar_rem_wakeup", "INTEGER DEFAULT NULL")

    conn.commit()


# def _add_column_if_missing(cursor, conn, table: str, column: str, definition: str) -> None:
#     """
#     Adds a column to an existing table only if it doesn't already exist.
#     Safe to call on every startup — idempotent.
#     """
#     cursor.execute(f"PRAGMA table_info({table})")
#     existing = {row[1] for row in cursor.fetchall()}
#     if column not in existing:
#         try:
#             cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
#             conn.commit()
#         except Exception:
#             pass  # concurrent startup race — column was added by another thread

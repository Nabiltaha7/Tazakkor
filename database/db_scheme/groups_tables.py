"""
database/db_scheme/groups_tables.py
─────────────────────────────────────
جداول المجموعات — PostgreSQL

Tables:
  - groups : المجموعات التي يعمل فيها البوت
"""
from database.connection import get_db_conn


def create_groups_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: groups
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id                 SERIAL  PRIMARY KEY,
        group_id           BIGINT  NOT NULL UNIQUE,
        name               TEXT    NOT NULL DEFAULT 'Unknown',
        joined_at          BIGINT  NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
        tz_offset          INTEGER NOT NULL DEFAULT 180,
        azkar_enabled      INTEGER NOT NULL DEFAULT 1,
        azkar_interval     INTEGER NOT NULL DEFAULT 15,
        azkar_rem_morning  INTEGER DEFAULT NULL,
        azkar_rem_evening  INTEGER DEFAULT NULL,
        azkar_rem_sleep    INTEGER DEFAULT NULL,
        azkar_rem_wakeup   INTEGER DEFAULT NULL
    )
    """)

    conn.commit()

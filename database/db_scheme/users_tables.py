"""
database/db_scheme/users_tables.py
────────────────────────────────────
جداول المستخدمين والتوقيت — PostgreSQL

Tables:
  - users          : هوية كل مستخدم تفاعل مع البوت
  - user_timezone  : توقيت UTC لكل مستخدم (يُستخدم في جميع التذكيرات)
"""
from database.connection import get_db_conn


def create_users_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: users
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id       SERIAL  PRIMARY KEY,
        user_id  BIGINT  NOT NULL UNIQUE,
        name     TEXT    NOT NULL DEFAULT '',
        username TEXT    DEFAULT NULL
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: user_timezone
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_timezone (
        id         SERIAL  PRIMARY KEY,
        user_id    BIGINT  NOT NULL UNIQUE,
        tz_offset  INTEGER NOT NULL DEFAULT 0,
        updated_at BIGINT  DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    conn.commit()

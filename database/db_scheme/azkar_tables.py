"""
database/db_scheme/azkar_tables.py
────────────────────────────────────
جداول الأذكار — PostgreSQL

Tables:
  - azkar           : نصوص الأذكار (صباح / مساء / نوم / استيقاظ)
  - azkar_progress  : تتبع تقدم المستخدم في جلسة الأذكار
  - azkar_reminders : تذكيرات الأذكار اليومية المجدولة
  - azkar_content   : أذكار للنشر التلقائي في المجموعات

zikr_type codes:
  0 = أذكار الصباح
  1 = أذكار المساء
  2 = أذكار النوم
  3 = أذكار الاستيقاظ
"""
from database.connection import get_db_conn


def create_azkar_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar (
        id           SERIAL  PRIMARY KEY,
        text         TEXT    NOT NULL,
        repeat_count INTEGER NOT NULL DEFAULT 1,
        zikr_type    INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_azkar_type ON azkar(zikr_type)
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar_progress
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_progress (
        id         SERIAL  PRIMARY KEY,
        user_id    BIGINT  NOT NULL,
        zikr_type  INTEGER NOT NULL,
        zikr_index INTEGER NOT NULL DEFAULT 0,
        remaining  INTEGER NOT NULL DEFAULT -1,
        UNIQUE (user_id, zikr_type),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar_reminders
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_reminders (
        id         SERIAL  PRIMARY KEY,
        user_id    BIGINT  NOT NULL,
        azkar_type INTEGER NOT NULL,
        hour       INTEGER NOT NULL,
        minute     INTEGER NOT NULL,
        created_at TEXT    NOT NULL DEFAULT NOW()::TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_azkar_reminders_user ON azkar_reminders(user_id)
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar_content
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_content (
        id      SERIAL PRIMARY KEY,
        content TEXT   NOT NULL UNIQUE
    )
    """)

    conn.commit()

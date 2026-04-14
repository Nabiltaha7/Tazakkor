"""
database/db_scheme/users_tables.py
────────────────────────────────────
جداول المستخدمين والتوقيت

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
    # PURPOSE: الجدول المركزي للهوية. كل مستخدم تيليغرام يحصل على
    #          صف واحد هنا. جميع الجداول الأخرى تشير إليه عبر user_id.
    #
    # COLUMNS:
    #   id       — مفتاح أساسي داخلي (autoincrement).
    #   user_id  — معرّف تيليغرام للمستخدم (فريد).
    #   name     — الاسم الكامل، يُحدَّث عند كل رسالة.
    #   username — اسم المستخدم (@username)، NULL إذا لم يُحدَّد.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL UNIQUE,
        name     TEXT    NOT NULL DEFAULT '',
        username TEXT    DEFAULT NULL
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: user_timezone
    # PURPOSE: يخزّن إزاحة UTC لكل مستخدم حتى تُرسَل التذكيرات
    #          في الوقت المحلي الصحيح. لا يُكرَّر التوقيت في أي
    #          جدول آخر — يُجلَب دائماً من هنا عبر JOIN.
    #
    # COLUMNS:
    #   id         — مفتاح أساسي داخلي.
    #   user_id    — يشير إلى users.user_id (صف واحد لكل مستخدم).
    #   tz_offset  — إزاحة UTC بالدقائق (مثال: UTC+3 = 180).
    #   updated_at — Unix timestamp لآخر تحديث.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_timezone (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL UNIQUE,
        tz_offset  INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    conn.commit()

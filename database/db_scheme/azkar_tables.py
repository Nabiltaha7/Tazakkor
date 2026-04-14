"""
database/db_scheme/azkar_tables.py
────────────────────────────────────
جداول الأذكار

Tables:
  - azkar           : نصوص الأذكار (صباح / مساء / نوم / استيقاظ)
  - azkar_progress  : تتبع تقدم المستخدم في جلسة الأذكار
  - azkar_reminders : تذكيرات الأذكار اليومية المجدولة

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
    # PURPOSE: يخزّن نصوص الأذكار مصنّفةً حسب النوع.
    #
    # COLUMNS:
    #   id           — مفتاح أساسي داخلي.
    #   text         — نص الذكر.
    #   repeat_count — عدد مرات التكرار المطلوبة.
    #   zikr_type    — نوع الذكر (0=صباح، 1=مساء، 2=نوم، 3=استيقاظ).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
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
    # PURPOSE: يتتبع موضع المستخدم في جلسة الأذكار الحالية حتى
    #          يتمكن من الإيقاف المؤقت والاستئناف.
    #
    # COLUMNS:
    #   id         — مفتاح أساسي داخلي.
    #   user_id    — يشير إلى users.user_id.
    #   zikr_type  — نوع الجلسة (نفس رموز azkar.zikr_type).
    #   zikr_index — فهرس الذكر الحالي في القائمة المرتبة.
    #   remaining  — التكرارات المتبقية للذكر الحالي.
    #                -1 تعني أن الجلسة لم تبدأ بعد.
    #
    # UNIQUE: (user_id, zikr_type) — صف تقدم واحد لكل جلسة لكل مستخدم.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_progress (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        zikr_type  INTEGER NOT NULL,
        zikr_index INTEGER NOT NULL DEFAULT 0,
        remaining  INTEGER NOT NULL DEFAULT -1,
        UNIQUE (user_id, zikr_type),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar_reminders
    # PURPOSE: تذكيرات يومية مجدولة تُرسَل رسالة خاصة للمستخدم
    #          في وقته المحلي المختار.
    #          التوقيت لا يُخزَّن هنا — يُجلَب دائماً من
    #          user_timezone.tz_offset عبر JOIN.
    #
    # COLUMNS:
    #   id         — مفتاح أساسي داخلي.
    #   user_id    — يشير إلى users.user_id.
    #   azkar_type — نوع الجلسة للتذكير (نفس رموز azkar.zikr_type).
    #   hour       — الساعة المحلية (0–23).
    #   minute     — الدقيقة المحلية (0–59).
    #   created_at — تاريخ إنشاء التذكير.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_reminders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        azkar_type INTEGER NOT NULL,
        hour       INTEGER NOT NULL,
        minute     INTEGER NOT NULL,
        created_at TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_azkar_reminders_user ON azkar_reminders(user_id)
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: azkar_content
    # PURPOSE: يخزّن أذكار مختارة للنشر التلقائي في المجموعات.
    #          مختلف عن جدول azkar الرئيسي (الذي يحتوي جلسات الأذكار).
    #          المحتوى فريد (UNIQUE) لمنع التكرار.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_content (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT    NOT NULL UNIQUE
    )
    """)

    conn.commit()

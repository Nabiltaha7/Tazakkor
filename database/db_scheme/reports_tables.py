"""
database/db_scheme/reports_tables.py
──────────────────────────────────────
جداول نظام التقارير والمطورين والتذاكر

Tables:
  - bot_constants  : إعدادات البوت القابلة للتعديل (مثل معرّف مجموعة المطورين)
  - bot_developers : قائمة مطوري البوت وأدوارهم
  - tickets        : تذاكر الدعم المُرسَلة من المستخدمين
  - ticket_messages: رسائل كل تذكرة (محادثة ثنائية)
  - ticket_limits  : الحد اليومي والكولداون لكل مستخدم
  - ticket_bans    : المستخدمون المحظورون من إرسال التذاكر
"""

from database.connection import get_db_conn


def create_reports_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: bot_constants
    # PURPOSE: إعدادات البوت الديناميكية القابلة للتعديل بدون إعادة
    #          تشغيل (مثل معرّف مجموعة المطورين).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_constants (
        name        TEXT    PRIMARY KEY,
        value       TEXT    NOT NULL,
        description TEXT    DEFAULT '',
        updated_at  INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: bot_developers
    # PURPOSE: يسجّل مطوري البوت وأدوارهم (primary / secondary).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_developers (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL UNIQUE,
        role     TEXT    NOT NULL DEFAULT 'secondary',
        added_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: tickets
    # PURPOSE: تذاكر الدعم المُرسَلة من المستخدمين.
    #
    # COLUMNS:
    #   user_id         — المستخدم صاحب التذكرة.
    #   chat_id         — المحادثة التي أُرسِلت منها التذكرة.
    #   category        — تصنيف التذكرة (اقتراح / مشكلة / ...).
    #   status          — حالة التذكرة: 'open' أو 'closed'.
    #   dev_group_msg_id— معرّف رسالة التذكرة في مجموعة المطورين.
    #   created_at      — Unix timestamp لوقت الإنشاء.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        chat_id          INTEGER NOT NULL,
        category         TEXT    NOT NULL,
        status           TEXT    NOT NULL DEFAULT 'open',
        dev_group_msg_id INTEGER DEFAULT NULL,
        created_at       INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_messages
    # PURPOSE: رسائل المحادثة داخل كل تذكرة (من المستخدم أو المطور).
    #
    # COLUMNS:
    #   ticket_id     — يشير إلى tickets.id.
    #   sender        — 'user' أو 'dev'.
    #   message_id    — معرّف رسالة تيليغرام.
    #   message_type  — نوع الرسالة: 'text' / 'photo' / 'document' / ...
    #   content       — نص الرسالة (إن وُجد).
    #   file_id       — معرّف الملف في تيليغرام (إن وُجد).
    #   file_unique_id— المعرّف الفريد للملف.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id      INTEGER NOT NULL,
        sender         TEXT    NOT NULL,
        message_id     INTEGER DEFAULT NULL,
        message_type   TEXT    NOT NULL DEFAULT 'text',
        content        TEXT    DEFAULT NULL,
        file_id        TEXT    DEFAULT NULL,
        file_unique_id TEXT    DEFAULT NULL,
        created_at     INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticket_messages ON ticket_messages(ticket_id)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_limits
    # PURPOSE: يتتبع الحد اليومي والكولداون لكل مستخدم لمنع الإساءة.
    #
    # COLUMNS:
    #   user_id   — المستخدم.
    #   date      — تاريخ اليوم (YYYY-MM-DD).
    #   count     — عدد التذاكر المُرسَلة اليوم.
    #   last_used — Unix timestamp لآخر تذكرة.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_limits (
        user_id   INTEGER NOT NULL,
        date      TEXT    NOT NULL,
        count     INTEGER NOT NULL DEFAULT 0,
        last_used INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_bans
    # PURPOSE: المستخدمون المحظورون من إرسال التذاكر.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_bans (
        user_id   INTEGER PRIMARY KEY,
        banned_at INTEGER DEFAULT (strftime('%s','now')),
        reason    TEXT    DEFAULT NULL
    )
    """)

    conn.commit()


def _seed_developers() -> None:
    """يُدرج المطورين الأساسيين والإعدادات الافتراضية إذا لم تكن موجودة."""
    from core.config import developers_id
    conn   = get_db_conn()
    cursor = conn.cursor()

    for dev_id in developers_id:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (dev_id,)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO bot_developers (user_id, role) VALUES (?, 'primary')",
            (dev_id,)
        )

    cursor.execute(
        "INSERT OR IGNORE INTO bot_constants (name, value, description) VALUES (?, ?, ?)",
        ("dev_group_id", "-1003505563946", "معرف مجموعة المطورين")
    )

    conn.commit()

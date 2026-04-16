"""
database/db_scheme/reports_tables.py
──────────────────────────────────────
جداول نظام التقارير والمطورين والتذاكر — PostgreSQL

Tables:
  - bot_constants  : إعدادات البوت القابلة للتعديل
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
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_constants (
        name        TEXT   PRIMARY KEY,
        value       TEXT   NOT NULL,
        description TEXT   DEFAULT '',
        updated_at  BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: bot_developers
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_developers (
        id       SERIAL PRIMARY KEY,
        user_id  BIGINT NOT NULL UNIQUE,
        role     TEXT   NOT NULL DEFAULT 'secondary',
        added_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: tickets
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id               SERIAL PRIMARY KEY,
        user_id          BIGINT NOT NULL,
        chat_id          BIGINT NOT NULL,
        category         TEXT   NOT NULL,
        status           TEXT   NOT NULL DEFAULT 'open',
        dev_group_msg_id BIGINT DEFAULT NULL,
        created_at       BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_messages
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id             SERIAL PRIMARY KEY,
        ticket_id      INTEGER NOT NULL,
        sender         TEXT    NOT NULL,
        message_id     BIGINT  DEFAULT NULL,
        message_type   TEXT    NOT NULL DEFAULT 'text',
        content        TEXT    DEFAULT NULL,
        file_id        TEXT    DEFAULT NULL,
        file_unique_id TEXT    DEFAULT NULL,
        created_at     BIGINT  DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticket_messages ON ticket_messages(ticket_id)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_limits
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_limits (
        user_id   BIGINT  NOT NULL,
        date      TEXT    NOT NULL,
        count     INTEGER NOT NULL DEFAULT 0,
        last_used BIGINT  NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: ticket_bans
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_bans (
        user_id   BIGINT PRIMARY KEY,
        banned_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
        reason    TEXT   DEFAULT NULL
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
            "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (dev_id,)
        )
        cursor.execute(
            "INSERT INTO bot_developers (user_id, role) VALUES (%s, 'primary') "
            "ON CONFLICT (user_id) DO NOTHING",
            (dev_id,)
        )

    # ── Default bot constants (only inserted if not already present) ──────────
    _defaults = [
        ("dev_group_id",        "-1003981603214", "معرف مجموعة المطورين"),
        # Kahf Friday reminder — local hour in UTC+3 (Yemen)
        ("KAHF_REMINDER_HOUR",  "7",              "ساعة تذكير سورة الكهف (توقيت اليمن UTC+3)"),
        # Azkar broadcast times — UTC hour when the scheduler fires
        ("MORNING_AZKAR_HOUR",  "4",              "ساعة إرسال أذكار الصباح (UTC)"),
        ("EVENING_AZKAR_HOUR",  "13",             "ساعة إرسال أذكار المساء (UTC)"),
    ]

    for name, value, description in _defaults:
        cursor.execute(
            """
            INSERT INTO bot_constants (name, value, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, value, description)
        )

    conn.commit()

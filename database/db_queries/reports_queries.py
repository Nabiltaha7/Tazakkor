"""
database/db_queries/reports_queries.py
────────────────────────────────────────
استعلامات جداول التذاكر والمطورين وإعدادات البوت

Tables: tickets, ticket_messages, ticket_limits, ticket_bans,
        bot_constants, bot_developers
"""
import time
from database.connection import get_db_conn

DAILY_TICKET_LIMIT = 2
TICKET_COOLDOWN_SEC = 10


# ══════════════════════════════════════════
# إعدادات البوت
# ══════════════════════════════════════════

def get_bot_constant(name: str) -> str | None:
    """يرجع قيمة إعداد بوت أو None."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT value FROM bot_constants WHERE name = ?", (name,))
    row = cur.fetchone()
    return row[0] if row else None


def set_bot_constant(name: str, value: str, description: str = "") -> None:
    """يُدرج أو يُحدّث إعداد بوت."""
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO bot_constants (name, value, description, updated_at)
        VALUES (?, ?, ?, strftime('%s','now'))
        ON CONFLICT(name) DO UPDATE SET
            value      = excluded.value,
            updated_at = excluded.updated_at
        """,
        (name, value, description)
    )
    conn.commit()


def get_all_constants() -> list[dict]:
    """يرجع جميع ثوابت البوت للعرض."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT name, value, description FROM bot_constants ORDER BY name")
    return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════
# المطورون
# ══════════════════════════════════════════

def is_developer(user_id: int) -> bool:
    cur = get_db_conn().cursor()
    cur.execute("SELECT 1 FROM bot_developers WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None


def get_developer(user_id: int) -> dict | None:
    """يرجع صف المطور أو None إذا لم يكن مطوراً."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM bot_developers WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_developers() -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM bot_developers ORDER BY added_at ASC")
    return [dict(r) for r in cur.fetchall()]


def upsert_developer(user_id: int, role: str = "secondary") -> None:
    """يُدرج أو يُحدّث دور المطور. آمن للاستدعاء مرتين."""
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO bot_developers (user_id, role)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
        """,
        (user_id, role)
    )
    conn.commit()


def remove_developer_db(user_id: int) -> bool:
    """يحذف المطور من قاعدة البيانات. يرجع True إذا تأثر صف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM bot_developers WHERE user_id = ?", (user_id,))
    conn.commit()
    return cur.rowcount > 0


# ══════════════════════════════════════════
# التذاكر
# ══════════════════════════════════════════

def create_ticket(user_id: int, chat_id: int, category: str) -> int:
    """يُنشئ تذكرة جديدة. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (user_id, chat_id, category) VALUES (?, ?, ?)",
        (user_id, chat_id, category)
    )
    conn.commit()
    return cur.lastrowid


def get_ticket(ticket_id: int) -> dict | None:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_open_ticket_for_user(user_id: int) -> dict | None:
    """يرجع آخر تذكرة مفتوحة للمستخدم."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT * FROM tickets WHERE user_id = ? AND status = 'open' "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_ticket_by_group_msg(msg_id: int) -> dict | None:
    """يجد التذكرة عبر رقم رسالة مجموعة المطورين."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM tickets WHERE dev_group_msg_id = ?", (msg_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_user_tickets(user_id: int, page: int = 0,
                     per_page: int = 5) -> list[dict]:
    """يرجع تذاكر مستخدم محدد مرتبةً من الأحدث."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT * FROM tickets WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, per_page, page * per_page)
    )
    return [dict(r) for r in cur.fetchall()]


def count_user_tickets(user_id: int) -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM tickets WHERE user_id = ?", (user_id,))
    return cur.fetchone()[0]


def get_tickets_paginated(status: str | None = None, page: int = 0,
                          per_page: int = 10) -> list[dict]:
    cur = get_db_conn().cursor()
    if status:
        cur.execute(
            """
            SELECT t.*, COUNT(tm.id) AS msg_count
            FROM tickets t
            LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
            WHERE t.status = ?
            GROUP BY t.id ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (status, per_page, page * per_page)
        )
    else:
        cur.execute(
            """
            SELECT t.*, COUNT(tm.id) AS msg_count
            FROM tickets t
            LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
            GROUP BY t.id ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, page * per_page)
        )
    return [dict(r) for r in cur.fetchall()]


def count_tickets(status: str | None = None) -> int:
    cur = get_db_conn().cursor()
    if status:
        cur.execute("SELECT COUNT(*) FROM tickets WHERE status = ?", (status,))
    else:
        cur.execute("SELECT COUNT(*) FROM tickets")
    return cur.fetchone()[0]


def close_ticket(ticket_id: int) -> None:
    conn = get_db_conn()
    conn.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
    conn.commit()


def set_ticket_group_msg(ticket_id: int, msg_id: int) -> None:
    conn = get_db_conn()
    conn.execute(
        "UPDATE tickets SET dev_group_msg_id = ? WHERE id = ?",
        (msg_id, ticket_id)
    )
    conn.commit()


def get_ticket_stats() -> dict:
    """يرجع إحصائيات التذاكر (اليوم، مفتوحة، مغلقة، الإجمالي)."""
    cur   = get_db_conn().cursor()
    today = time.strftime("%Y-%m-%d")

    cur.execute(
        "SELECT COUNT(*) FROM tickets WHERE date(created_at, 'unixepoch') = ?",
        (today,)
    )
    today_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
    open_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
    closed_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets")
    total_count = cur.fetchone()[0]

    return {
        "today":  today_count,
        "open":   open_count,
        "closed": closed_count,
        "total":  total_count,
    }


# ══════════════════════════════════════════
# رسائل التذاكر
# ══════════════════════════════════════════

def add_ticket_message(ticket_id: int, sender: str, message_id: int = None,
                       message_type: str = "text", content: str = None,
                       file_id: str = None, file_unique_id: str = None) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        """
        INSERT INTO ticket_messages
            (ticket_id, sender, message_id, message_type, content, file_id, file_unique_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, sender, message_id, message_type, content, file_id, file_unique_id)
    )
    conn.commit()
    return cur.lastrowid


def get_ticket_messages(ticket_id: int, limit: int = 20) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT * FROM ticket_messages WHERE ticket_id = ? "
        "ORDER BY created_at ASC LIMIT ?",
        (ticket_id, limit)
    )
    return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════
# الحدود اليومية والكولداون
# ══════════════════════════════════════════

def check_ticket_limits(user_id: int) -> tuple[bool, str | None]:
    """
    يتحقق من الحد اليومي والكولداون.
    يرجع (True, None) إذا مسموح، أو (False, رسالة_خطأ).
    """
    cur   = get_db_conn().cursor()
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())

    cur.execute(
        "SELECT count, last_used FROM ticket_limits WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    row = cur.fetchone()

    if row:
        count, last_used = row[0], row[1]
        elapsed = now - last_used
        if elapsed < TICKET_COOLDOWN_SEC:
            return False, f"⏳ انتظر {TICKET_COOLDOWN_SEC - elapsed} ثانية قبل إرسال تذكرة جديدة."
        if count >= DAILY_TICKET_LIMIT:
            return False, f"❌ وصلت للحد اليومي ({DAILY_TICKET_LIMIT} تذاكر). حاول غداً."

    return True, None


def record_ticket_usage(user_id: int) -> None:
    conn  = get_db_conn()
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())
    conn.execute(
        """
        INSERT INTO ticket_limits (user_id, date, count, last_used)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            count     = count + 1,
            last_used = ?
        """,
        (user_id, today, now, now)
    )
    conn.commit()


# ══════════════════════════════════════════
# حظر المستخدمين من التذاكر
# ══════════════════════════════════════════

def ban_ticket_user(user_id: int, reason: str = None) -> None:
    conn = get_db_conn()
    conn.execute(
        "INSERT OR REPLACE INTO ticket_bans (user_id, banned_at, reason) "
        "VALUES (?, strftime('%s','now'), ?)",
        (user_id, reason)
    )
    conn.commit()


def unban_ticket_user(user_id: int) -> None:
    conn = get_db_conn()
    conn.execute("DELETE FROM ticket_bans WHERE user_id = ?", (user_id,))
    conn.commit()


def is_ticket_banned(user_id: int) -> bool:
    cur = get_db_conn().cursor()
    cur.execute("SELECT 1 FROM ticket_bans WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None


def get_banned_users_paginated(page: int = 0,
                                per_page: int = 20) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute(
        """
        SELECT b.user_id, b.banned_at, COALESCE(u.name, '') AS name
        FROM ticket_bans b
        LEFT JOIN users u ON u.user_id = b.user_id
        ORDER BY b.banned_at DESC
        LIMIT ? OFFSET ?
        """,
        (per_page, page * per_page)
    )
    return [dict(zip(("user_id", "banned_at", "name"), row)) for row in cur.fetchall()]


def count_banned_users() -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM ticket_bans")
    return cur.fetchone()[0]

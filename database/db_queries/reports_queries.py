"""
database/db_queries/reports_queries.py
────────────────────────────────────────
استعلامات جداول التذاكر والمطورين وإعدادات البوت — PostgreSQL

Tables: tickets, ticket_messages, ticket_limits, ticket_bans,
        bot_constants, bot_developers
"""
import time
from database.connection import get_db_conn, db_execute, db_fetchone, db_fetchall

DAILY_TICKET_LIMIT  = 2
TICKET_COOLDOWN_SEC = 10


# ══════════════════════════════════════════
# إعدادات البوت
# ══════════════════════════════════════════

def get_bot_constant(name: str) -> str | None:
    """يرجع قيمة إعداد بوت أو None."""
    row = db_fetchone("SELECT value FROM bot_constants WHERE name = %s", (name,))
    return row["value"] if row else None


def set_bot_constant(name: str, value: str, description: str = "") -> None:
    """يُدرج أو يُحدّث إعداد بوت ويُحدّث الذاكرة فوراً."""
    db_execute(
        """
        INSERT INTO bot_constants (name, value, description, updated_at)
        VALUES (%s, %s, %s, EXTRACT(EPOCH FROM NOW())::INTEGER)
        ON CONFLICT (name) DO UPDATE SET
            value      = EXCLUDED.value,
            updated_at = EXCLUDED.updated_at
        """,
        (name, value, description)
    )
    # Update in-memory cache immediately — no need to wait for next sync cycle
    try:
        from core.config import set_config
        set_config(name, value)
    except Exception as e:
        print(f"[Config] Failed to update in-memory cache for {name!r}: {e}")


def get_all_constants() -> list[dict]:
    """يرجع جميع ثوابت البوت للعرض."""
    return db_fetchall("SELECT name, value, description FROM bot_constants ORDER BY name")


# ══════════════════════════════════════════
# المطورون
# ══════════════════════════════════════════

def is_developer(user_id: int) -> bool:
    return db_fetchone(
        "SELECT 1 AS found FROM bot_developers WHERE user_id = %s", (user_id,)
    ) is not None


def get_developer(user_id: int) -> dict | None:
    """يرجع صف المطور أو None إذا لم يكن مطوراً."""
    return db_fetchone("SELECT * FROM bot_developers WHERE user_id = %s", (user_id,))


def get_all_developers() -> list[dict]:
    return db_fetchall("SELECT * FROM bot_developers ORDER BY added_at ASC")


def upsert_developer(user_id: int, role: str = "secondary") -> None:
    """يُدرج أو يُحدّث دور المطور. آمن للاستدعاء مرتين."""
    db_execute(
        """
        INSERT INTO bot_developers (user_id, role)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET role = EXCLUDED.role
        """,
        (user_id, role)
    )


def remove_developer_db(user_id: int) -> bool:
    """يحذف المطور من قاعدة البيانات. يرجع True إذا تأثر صف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM bot_developers WHERE user_id = %s", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# ══════════════════════════════════════════
# التذاكر
# ══════════════════════════════════════════

def create_ticket(user_id: int, chat_id: int, category: str) -> int:
    """يُنشئ تذكرة جديدة. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tickets (user_id, chat_id, category) VALUES (%s, %s, %s) RETURNING id",
            (user_id, chat_id, category)
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def get_ticket(ticket_id: int) -> dict | None:
    return db_fetchone("SELECT * FROM tickets WHERE id = %s", (ticket_id,))


def get_open_ticket_for_user(user_id: int) -> dict | None:
    """يرجع آخر تذكرة مفتوحة للمستخدم."""
    return db_fetchone(
        "SELECT * FROM tickets WHERE user_id = %s AND status = 'open' "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )


def get_ticket_by_group_msg(msg_id: int) -> dict | None:
    """يجد التذكرة عبر رقم رسالة مجموعة المطورين."""
    return db_fetchone("SELECT * FROM tickets WHERE dev_group_msg_id = %s", (msg_id,))


def get_user_tickets(user_id: int, page: int = 0,
                     per_page: int = 5) -> list[dict]:
    """يرجع تذاكر مستخدم محدد مرتبةً من الأحدث."""
    return db_fetchall(
        "SELECT * FROM tickets WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (user_id, per_page, page * per_page)
    )


def count_user_tickets(user_id: int) -> int:
    row = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets WHERE user_id = %s", (user_id,))
    return row["cnt"] if row else 0


def get_tickets_paginated(status: str | None = None, page: int = 0,
                          per_page: int = 10) -> list[dict]:
    if status:
        return db_fetchall(
            """
            SELECT t.*, COUNT(tm.id) AS msg_count
            FROM tickets t
            LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
            WHERE t.status = %s
            GROUP BY t.id ORDER BY t.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (status, per_page, page * per_page)
        )
    return db_fetchall(
        """
        SELECT t.*, COUNT(tm.id) AS msg_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        GROUP BY t.id ORDER BY t.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (per_page, page * per_page)
    )


def count_tickets(status: str | None = None) -> int:
    if status:
        row = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets WHERE status = %s", (status,))
    else:
        row = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets")
    return row["cnt"] if row else 0


def close_ticket(ticket_id: int) -> None:
    db_execute("UPDATE tickets SET status = 'closed' WHERE id = %s", (ticket_id,))


def set_ticket_group_msg(ticket_id: int, msg_id: int) -> None:
    db_execute(
        "UPDATE tickets SET dev_group_msg_id = %s WHERE id = %s",
        (msg_id, ticket_id)
    )


def get_ticket_stats() -> dict:
    """يرجع إحصائيات التذاكر (اليوم، مفتوحة، مغلقة، الإجمالي)."""
    today = time.strftime("%Y-%m-%d")

    # created_at is stored as Unix timestamp (BIGINT)
    today_row  = db_fetchone(
        "SELECT COUNT(*) AS cnt FROM tickets "
        "WHERE TO_CHAR(TO_TIMESTAMP(created_at), 'YYYY-MM-DD') = %s",
        (today,)
    )
    open_row   = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets WHERE status = 'open'")
    closed_row = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets WHERE status = 'closed'")
    total_row  = db_fetchone("SELECT COUNT(*) AS cnt FROM tickets")

    return {
        "today":  today_row["cnt"]  if today_row  else 0,
        "open":   open_row["cnt"]   if open_row   else 0,
        "closed": closed_row["cnt"] if closed_row else 0,
        "total":  total_row["cnt"]  if total_row  else 0,
    }


# ══════════════════════════════════════════
# رسائل التذاكر
# ══════════════════════════════════════════

def add_ticket_message(ticket_id: int, sender: str, message_id: int = None,
                       message_type: str = "text", content: str = None,
                       file_id: str = None, file_unique_id: str = None) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO ticket_messages
                (ticket_id, sender, message_id, message_type, content, file_id, file_unique_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ticket_id, sender, message_id, message_type, content, file_id, file_unique_id)
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def get_ticket_messages(ticket_id: int, limit: int = 20) -> list[dict]:
    return db_fetchall(
        "SELECT * FROM ticket_messages WHERE ticket_id = %s "
        "ORDER BY created_at ASC LIMIT %s",
        (ticket_id, limit)
    )


# ══════════════════════════════════════════
# الحدود اليومية والكولداون
# ══════════════════════════════════════════

def check_ticket_limits(user_id: int) -> tuple[bool, str | None]:
    """
    يتحقق من الحد اليومي والكولداون.
    يرجع (True, None) إذا مسموح، أو (False, رسالة_خطأ).
    """
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())

    row = db_fetchone(
        "SELECT count, last_used FROM ticket_limits WHERE user_id = %s AND date = %s",
        (user_id, today)
    )

    if row:
        count, last_used = row["count"], row["last_used"]
        elapsed = now - last_used
        if elapsed < TICKET_COOLDOWN_SEC:
            return False, f"⏳ انتظر {TICKET_COOLDOWN_SEC - elapsed} ثانية قبل إرسال تذكرة جديدة."
        if count >= DAILY_TICKET_LIMIT:
            return False, f"❌ وصلت للحد اليومي ({DAILY_TICKET_LIMIT} تذاكر). حاول غداً."

    return True, None


def record_ticket_usage(user_id: int) -> None:
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())
    db_execute(
        """
        INSERT INTO ticket_limits (user_id, date, count, last_used)
        VALUES (%s, %s, 1, %s)
        ON CONFLICT (user_id, date) DO UPDATE SET
            count     = ticket_limits.count + 1,
            last_used = %s
        """,
        (user_id, today, now, now)
    )


# ══════════════════════════════════════════
# حظر المستخدمين من التذاكر
# ══════════════════════════════════════════

def ban_ticket_user(user_id: int, reason: str = None) -> None:
    db_execute(
        """
        INSERT INTO ticket_bans (user_id, banned_at, reason)
        VALUES (%s, EXTRACT(EPOCH FROM NOW())::INTEGER, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            banned_at = EXCLUDED.banned_at,
            reason    = EXCLUDED.reason
        """,
        (user_id, reason)
    )


def unban_ticket_user(user_id: int) -> None:
    db_execute("DELETE FROM ticket_bans WHERE user_id = %s", (user_id,))


def is_ticket_banned(user_id: int) -> bool:
    return db_fetchone(
        "SELECT 1 AS found FROM ticket_bans WHERE user_id = %s", (user_id,)
    ) is not None


def get_banned_users_paginated(page: int = 0,
                                per_page: int = 20) -> list[dict]:
    return db_fetchall(
        """
        SELECT b.user_id, b.banned_at, COALESCE(u.name, '') AS name
        FROM ticket_bans b
        LEFT JOIN users u ON u.user_id = b.user_id
        ORDER BY b.banned_at DESC
        LIMIT %s OFFSET %s
        """,
        (per_page, page * per_page)
    )


def count_banned_users() -> int:
    row = db_fetchone("SELECT COUNT(*) AS cnt FROM ticket_bans")
    return row["cnt"] if row else 0

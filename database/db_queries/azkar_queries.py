"""
database/db_queries/azkar_queries.py
──────────────────────────────────────
استعلامات جداول azkar وazkar_progress وazkar_reminders — PostgreSQL

zikr_type codes:
  0 = أذكار الصباح
  1 = أذكار المساء
  2 = أذكار النوم
  3 = أذكار الاستيقاظ
"""
from database.connection import get_db_conn, db_execute, db_fetchone, db_fetchall


# ══════════════════════════════════════════
# الأذكار
# ══════════════════════════════════════════

def get_azkar_list(zikr_type: int) -> list[dict]:
    """يرجع قائمة الأذكار لنوع معين مرتبةً بالـ id."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT id, text, repeat_count, zikr_type FROM azkar WHERE zikr_type = %s ORDER BY id",
        (zikr_type,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_zikr(zikr_id: int) -> dict | None:
    """يرجع ذكراً واحداً بمعرّفه أو None."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM azkar WHERE id = %s", (zikr_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def add_zikr(text: str, repeat_count: int, zikr_type: int) -> int:
    """يُضيف ذكراً جديداً. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO azkar (text, repeat_count, zikr_type) VALUES (%s, %s, %s) RETURNING id",
        (text.strip(), repeat_count, zikr_type),
    )
    row = cur.fetchone()
    conn.commit()
    return row["id"] if row else 0


def update_zikr(zikr_id: int, text: str, repeat_count: int) -> bool:
    """يُحدّث نص وعدد تكرار ذكر. يرجع True إذا تأثر صف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE azkar SET text = %s, repeat_count = %s WHERE id = %s",
        (text.strip(), repeat_count, zikr_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_zikr(zikr_id: int) -> bool:
    """يحذف ذكراً. يرجع True إذا تأثر صف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM azkar WHERE id = %s", (zikr_id,))
    conn.commit()
    return cur.rowcount > 0


def zikr_exists(zikr_type: int) -> bool:
    """يتحقق من وجود أي أذكار لنوع معين."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT 1 FROM azkar WHERE zikr_type = %s LIMIT 1", (zikr_type,))
    return cur.fetchone() is not None


# ══════════════════════════════════════════
# تقدم المستخدم
# ══════════════════════════════════════════

def get_azkar_progress(user_id: int, zikr_type: int) -> dict:
    """
    يرجع تقدم المستخدم في جلسة الأذكار.
    يرجع {'zikr_index': 0, 'remaining': -1} إذا لم تبدأ الجلسة.
    """
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT zikr_index, remaining FROM azkar_progress WHERE user_id = %s AND zikr_type = %s",
        (user_id, zikr_type),
    )
    row = cur.fetchone()
    return {"zikr_index": row["zikr_index"], "remaining": row["remaining"]} if row \
        else {"zikr_index": 0, "remaining": -1}


def save_azkar_progress(user_id: int, zikr_type: int,
                        zikr_index: int, remaining: int) -> None:
    """يحفظ أو يُحدّث تقدم المستخدم في جلسة الأذكار."""
    db_execute(
        """
        INSERT INTO azkar_progress (user_id, zikr_type, zikr_index, remaining)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, zikr_type) DO UPDATE SET
            zikr_index = EXCLUDED.zikr_index,
            remaining  = EXCLUDED.remaining
        """,
        (user_id, zikr_type, zikr_index, remaining),
    )


def reset_azkar_progress(user_id: int, zikr_type: int) -> None:
    """يحذف تقدم المستخدم في جلسة معينة (إعادة تعيين)."""
    db_execute(
        "DELETE FROM azkar_progress WHERE user_id = %s AND zikr_type = %s",
        (user_id, zikr_type),
    )


# ══════════════════════════════════════════
# تذكيرات الأذكار
# ══════════════════════════════════════════

def add_azkar_reminder(user_id: int, azkar_type: int,
                       hour: int, minute: int) -> int:
    """يُضيف تذكيراً. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO azkar_reminders (user_id, azkar_type, hour, minute) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (user_id, azkar_type, hour, minute),
    )
    row = cur.fetchone()
    conn.commit()
    return row["id"] if row else 0


def get_user_azkar_reminders(user_id: int) -> list[dict]:
    """يرجع جميع تذكيرات المستخدم مرتبةً بالوقت."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT id, user_id, azkar_type, hour, minute, created_at "
        "FROM azkar_reminders WHERE user_id = %s ORDER BY hour, minute",
        (user_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def delete_azkar_reminder(reminder_id: int, user_id: int) -> bool:
    """يحذف تذكيراً. يرجع True إذا تأثر صف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM azkar_reminders WHERE id = %s AND user_id = %s",
        (reminder_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def count_user_azkar_reminders(user_id: int) -> int:
    """يرجع عدد تذكيرات المستخدم."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM azkar_reminders WHERE user_id = %s", (user_id,))
    return cur.fetchone()["cnt"]


def get_due_azkar_reminders(utc_hour: int, utc_minute: int) -> list[dict]:
    """
    يرجع التذكيرات التي يتطابق وقتها المحلي مع utc_hour:utc_minute.
    يجلب التوقيت من جدول user_timezone عبر JOIN.
    """
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT r.id, r.user_id, r.azkar_type, r.hour, r.minute,
               COALESCE(tz.tz_offset, 0) AS tz_offset
        FROM azkar_reminders r
        LEFT JOIN user_timezone tz ON tz.user_id = r.user_id
    """)
    due = []
    for r in cur.fetchall():
        r = dict(r)
        local_total = r["hour"] * 60 + r["minute"]
        utc_total   = (local_total - r["tz_offset"]) % (24 * 60)
        if utc_total == utc_hour * 60 + utc_minute:
            due.append(r)
    return due


# ══════════════════════════════════════════
# محتوى الأذكار (للنشر التلقائي في المجموعات)
# ══════════════════════════════════════════

def get_random_azkar_content() -> dict | None:
    """يجلب ذكراً عشوائياً من azkar_content بكفاءة."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT * FROM azkar_content OFFSET FLOOR(RANDOM() * "
        "(SELECT COUNT(*) FROM azkar_content)) LIMIT 1"
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_azkar_content_by_id(row_id: int) -> dict | None:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM azkar_content WHERE id = %s", (row_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def count_azkar_content() -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM azkar_content")
    return cur.fetchone()["cnt"]


def insert_azkar_content(content: str) -> int:
    """يُدرج ذكراً جديداً (يتجاهل التكرار). يرجع id الصف."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO azkar_content (content) VALUES (%s) "
        "ON CONFLICT (content) DO NOTHING RETURNING id",
        (content.strip(),)
    )
    row = cur.fetchone()
    conn.commit()
    return row["id"] if row else 0


def update_azkar_content(row_id: int, content: str) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE azkar_content SET content = %s WHERE id = %s",
        (content.strip(), row_id)
    )
    conn.commit()
    return cur.rowcount > 0


def delete_azkar_content(row_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM azkar_content WHERE id = %s", (row_id,))
    conn.commit()
    return cur.rowcount > 0

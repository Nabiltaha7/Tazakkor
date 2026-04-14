"""
database/db_queries/groups_queries.py
───────────────────────────────────────
استعلامات جداول groups وgroup_members
"""
from database.connection import get_db_conn, db_write


# ══════════════════════════════════════════
# مساعدات داخلية
# ══════════════════════════════════════════

def _get_or_create_group(cursor, tg_group_id: int, group_name: str) -> int:
    """
    يرجع groups.id الداخلي لمعرّف مجموعة تيليغرام.
    يُدرج المجموعة إذا لم تكن موجودة.
    يجب استدعاؤه داخل transaction قائمة.
    """
    cursor.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO groups (group_id, name) VALUES (?, ?)",
        (tg_group_id, group_name or "Unknown")
    )
    return cursor.lastrowid


# ══════════════════════════════════════════
# قراءة
# ══════════════════════════════════════════

def get_internal_group_id(tg_group_id: int) -> int | None:
    """يرجع groups.id لمعرّف تيليغرام، أو None إذا لم يُوجد."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cur.fetchone()
    return row[0] if row else None


def get_group(tg_group_id: int) -> dict | None:
    """يرجع صف المجموعة كاملاً أو None."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_group_ids() -> list[int]:
    """يرجع قائمة بجميع group_id (معرّفات تيليغرام) المسجلة."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT group_id FROM groups")
    return [r[0] for r in cur.fetchall()]


def get_group_setting(tg_group_id: int, column: str) -> int | None:
    """
    يرجع قيمة عمود إعداد واحد من جدول groups.
    مثال: get_group_setting(gid, 'azkar_enabled')
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return None
    cur = get_db_conn().cursor()
    cur.execute(f"SELECT {column} FROM groups WHERE id = ?", (internal_id,))
    row = cur.fetchone()
    return row[0] if row else None


# ══════════════════════════════════════════
# كتابة
# ══════════════════════════════════════════

def upsert_group(tg_group_id: int, group_name: str) -> int:
    """يُدرج أو يُحدّث المجموعة. يرجع groups.id الداخلي."""
    def _write():
        conn   = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO groups (group_id, name)
            VALUES (?, ?)
            ON CONFLICT(group_id) DO UPDATE SET name = excluded.name
            """,
            (tg_group_id, group_name or "Unknown")
        )
        conn.commit()
        cursor.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
        return cursor.fetchone()[0]

    return db_write(_write)


def upsert_user_identity(user_id: int, full_name: str, username: str = None) -> None:
    """يضمن وجود المستخدم في جدول users ويُحدّث اسمه."""
    full_name = (full_name or "").strip() or "Unknown"
    username  = (username  or "").strip() or None

    def _write():
        conn = get_db_conn()
        conn.execute(
            """
            INSERT INTO users (user_id, name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name     = excluded.name,
                username = excluded.username
            """,
            (user_id, full_name, username)
        )
        conn.commit()

    db_write(_write)


def set_group_setting(tg_group_id: int, column: str, value: int) -> bool:
    """
    يُحدّث عمود إعداد واحد في جدول groups.
    مثال: set_group_setting(gid, 'azkar_enabled', 1)
    يرجع True إذا نجح التحديث.
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn = get_db_conn()
    conn.execute(
        f"UPDATE groups SET {column} = ? WHERE id = ?",
        (value, internal_id)
    )
    conn.commit()
    return True


# ══════════════════════════════════════════
# إعدادات المجموعة (tz، أذكار، فترة الإرسال)
# ══════════════════════════════════════════

# أعمدة الإعدادات المسموح بتعديلها
_ALLOWED_SETTINGS = {
    "tz_offset", "azkar_enabled", "azkar_interval",
    "azkar_rem_morning", "azkar_rem_evening",
    "azkar_rem_sleep", "azkar_rem_wakeup",
}


def get_group_settings(tg_group_id: int) -> dict:
    """
    يرجع dict بجميع إعدادات المجموعة.
    يرجع قيماً افتراضية إذا لم تكن المجموعة مسجلة.
    """
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT tz_offset, azkar_enabled, azkar_interval, "
        "azkar_rem_morning, azkar_rem_evening, azkar_rem_sleep, azkar_rem_wakeup "
        "FROM groups WHERE group_id = ?",
        (tg_group_id,)
    )
    row = cur.fetchone()
    if row:
        return dict(row)
    return {
        "tz_offset":        180,
        "azkar_enabled":    0,
        "azkar_interval":   15,
        "azkar_rem_morning":  None,
        "azkar_rem_evening":  None,
        "azkar_rem_sleep":    None,
        "azkar_rem_wakeup":   None,
    }


def update_group_setting(tg_group_id: int, column: str, value) -> bool:
    """
    يُحدّث عمود إعداد واحد للمجموعة.
    يرجع True إذا نجح التحديث.
    """
    if column not in _ALLOWED_SETTINGS:
        return False
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn = get_db_conn()
    conn.execute(
        f"UPDATE groups SET {column} = ? WHERE id = ?",
        (value, internal_id)
    )
    conn.commit()
    return True


def get_groups_with_reminder(reminder_col: str) -> list[dict]:
    """
    يرجع المجموعات التي لها تذكير مُعيَّن لنوع أذكار معين.
    reminder_col: azkar_rem_morning | azkar_rem_evening | azkar_rem_sleep | azkar_rem_wakeup
    """
    if reminder_col not in _ALLOWED_SETTINGS:
        return []
    cur = get_db_conn().cursor()
    cur.execute(
        f"SELECT group_id, tz_offset, {reminder_col} AS hour "
        f"FROM groups WHERE {reminder_col} IS NOT NULL",
    )
    return [dict(r) for r in cur.fetchall()]

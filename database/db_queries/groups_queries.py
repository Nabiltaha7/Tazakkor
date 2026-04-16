"""
database/db_queries/groups_queries.py
───────────────────────────────────────
استعلامات جدول groups — PostgreSQL
"""
from database.connection import get_db_conn, db_write, db_execute, db_fetchone, db_fetchall


# ══════════════════════════════════════════
# قراءة
# ══════════════════════════════════════════

def get_internal_group_id(tg_group_id: int) -> int | None:
    """يرجع groups.id لمعرّف تيليغرام، أو None إذا لم يُوجد."""
    row = db_fetchone("SELECT id FROM groups WHERE group_id = %s", (tg_group_id,))
    return row["id"] if row else None


def get_group(tg_group_id: int) -> dict | None:
    """يرجع صف المجموعة كاملاً أو None."""
    return db_fetchone("SELECT * FROM groups WHERE group_id = %s", (tg_group_id,))


def get_all_group_ids() -> list[int]:
    """يرجع قائمة بجميع group_id (معرّفات تيليغرام) المسجلة."""
    rows = db_fetchall("SELECT group_id FROM groups")
    return [r["group_id"] for r in rows]


def get_group_setting(tg_group_id: int, column: str) -> int | None:
    """
    يرجع قيمة عمود إعداد واحد من جدول groups.
    مثال: get_group_setting(gid, 'azkar_enabled')
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return None
    row = db_fetchone(f"SELECT {column} FROM groups WHERE id = %s", (internal_id,))
    return row[column] if row else None


# ══════════════════════════════════════════
# كتابة
# ══════════════════════════════════════════

def upsert_group(tg_group_id: int, group_name: str) -> int:
    """يُدرج أو يُحدّث المجموعة. يرجع groups.id الداخلي."""
    def _write():
        conn = get_db_conn()
        cur  = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO groups (group_id, name)
                VALUES (%s, %s)
                ON CONFLICT (group_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (tg_group_id, group_name or "Unknown")
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"]
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    return db_write(_write)


def upsert_user_identity(user_id: int, full_name: str, username: str = None) -> None:
    """يضمن وجود المستخدم في جدول users ويُحدّث اسمه."""
    full_name = (full_name or "").strip() or "Unknown"
    username  = (username  or "").strip() or None

    def _write():
        db_execute(
            """
            INSERT INTO users (user_id, name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                name     = EXCLUDED.name,
                username = EXCLUDED.username
            """,
            (user_id, full_name, username)
        )

    db_write(_write)


def set_group_setting(tg_group_id: int, column: str, value: int) -> bool:
    """
    يُحدّث عمود إعداد واحد في جدول groups.
    يرجع True إذا نجح التحديث.
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    db_execute(
        f"UPDATE groups SET {column} = %s WHERE id = %s",
        (value, internal_id)
    )
    return True


# ══════════════════════════════════════════
# إعدادات المجموعة
# ══════════════════════════════════════════

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
    row = db_fetchone(
        "SELECT tz_offset, azkar_enabled, azkar_interval, "
        "azkar_rem_morning, azkar_rem_evening, azkar_rem_sleep, azkar_rem_wakeup "
        "FROM groups WHERE group_id = %s",
        (tg_group_id,)
    )
    if row:
        return row
    return {
        "tz_offset":          180,
        "azkar_enabled":      0,
        "azkar_interval":     15,
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
    db_execute(
        f"UPDATE groups SET {column} = %s WHERE id = %s",
        (value, internal_id)
    )
    return True


def get_groups_with_reminder(reminder_col: str) -> list[dict]:
    """
    يرجع المجموعات التي لها تذكير مُعيَّن لنوع أذكار معين.
    reminder_col: azkar_rem_morning | azkar_rem_evening | azkar_rem_sleep | azkar_rem_wakeup
    """
    if reminder_col not in _ALLOWED_SETTINGS:
        return []
    return db_fetchall(
        f"SELECT group_id, tz_offset, {reminder_col} AS hour "
        f"FROM groups WHERE {reminder_col} IS NOT NULL"
    )

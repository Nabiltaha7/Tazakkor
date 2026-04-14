"""
database/db_queries/users_queries.py
──────────────────────────────────────
استعلامات جدول users وuser_timezone
"""
from database.connection import get_db_conn, db_write


# ══════════════════════════════════════════
# قراءة
# ══════════════════════════════════════════

def get_user(user_id: int) -> dict | None:
    """يرجع صف المستخدم كاملاً أو None."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_user_name(user_id: int) -> str:
    """يرجع اسم المستخدم أو سلسلة فارغة."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return (row[0] or "").strip() if row else ""


def get_user_id_by_username(username: str) -> tuple[int | None, str | None]:
    """
    يبحث عن user_id بناءً على @username (بدون أو مع @).
    يرجع (user_id, name) أو (None, None) إذا لم يُوجد.
    """
    uname = username.lstrip("@").lower()
    cur   = get_db_conn().cursor()
    cur.execute(
        "SELECT user_id, name FROM users WHERE LOWER(username) = ?",
        (uname,)
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)


def get_all_user_ids() -> list[int]:
    """يرجع قائمة بجميع user_id المسجلين."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT user_id FROM users")
    return [r[0] for r in cur.fetchall()]


# ══════════════════════════════════════════
# كتابة
# ══════════════════════════════════════════

def upsert_user(user_id: int, name: str, username: str = None) -> None:
    """يُدرج أو يُحدّث بيانات المستخدم."""
    name     = (name     or "").strip() or "Unknown"
    username = (username or "").strip() or None

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
            (user_id, name, username)
        )
        conn.commit()

    db_write(_write)


def ensure_user_exists(user_id: int) -> None:
    """يُدرج المستخدم بقيم افتراضية إذا لم يكن موجوداً."""
    conn = get_db_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


# ══════════════════════════════════════════
# التوقيت
# ══════════════════════════════════════════

def get_user_tz(user_id: int) -> int | None:
    """يرجع tz_offset بالدقائق، أو None إذا لم يُحدَّد بعد."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT tz_offset FROM user_timezone WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def set_user_tz(user_id: int, tz_offset: int) -> None:
    """يحفظ أو يُحدّث توقيت المستخدم (بالدقائق)."""
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO user_timezone (user_id, tz_offset, updated_at)
        VALUES (?, ?, strftime('%s','now'))
        ON CONFLICT(user_id) DO UPDATE SET
            tz_offset  = excluded.tz_offset,
            updated_at = excluded.updated_at
        """,
        (user_id, tz_offset)
    )
    conn.commit()

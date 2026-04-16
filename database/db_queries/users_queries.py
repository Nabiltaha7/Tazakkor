"""
database/db_queries/users_queries.py
──────────────────────────────────────
استعلامات جدول users وuser_timezone — PostgreSQL
"""
from database.connection import get_db_conn, db_write, db_execute, db_fetchone


# ══════════════════════════════════════════
# قراءة
# ══════════════════════════════════════════

def get_user(user_id: int) -> dict | None:
    """يرجع صف المستخدم كاملاً أو None."""
    return db_fetchone("SELECT * FROM users WHERE user_id = %s", (user_id,))


def get_user_name(user_id: int) -> str:
    """يرجع اسم المستخدم أو سلسلة فارغة."""
    row = db_fetchone("SELECT name FROM users WHERE user_id = %s", (user_id,))
    return (row["name"] or "").strip() if row else ""


def get_user_id_by_username(username: str) -> tuple[int | None, str | None]:
    """
    يبحث عن user_id بناءً على @username (بدون أو مع @).
    يرجع (user_id, name) أو (None, None) إذا لم يُوجد.
    """
    uname = username.lstrip("@").lower()
    row   = db_fetchone(
        "SELECT user_id, name FROM users WHERE LOWER(username) = %s",
        (uname,)
    )
    return (row["user_id"], row["name"]) if row else (None, None)


def get_all_user_ids() -> list[int]:
    """يرجع قائمة بجميع user_id المسجلين."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    cur.close()
    return [r["user_id"] for r in rows]


# ══════════════════════════════════════════
# كتابة
# ══════════════════════════════════════════

def upsert_user(user_id: int, name: str, username: str = None) -> None:
    """يُدرج أو يُحدّث بيانات المستخدم."""
    name     = (name     or "").strip() or "Unknown"
    username = (username or "").strip() or None

    def _write():
        db_execute(
            """
            INSERT INTO users (user_id, name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                name     = EXCLUDED.name,
                username = EXCLUDED.username
            """,
            (user_id, name, username)
        )

    db_write(_write)


def ensure_user_exists(user_id: int) -> None:
    """يُدرج المستخدم بقيم افتراضية إذا لم يكن موجوداً."""
    db_execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,)
    )


# ══════════════════════════════════════════
# التوقيت
# ══════════════════════════════════════════

def get_user_tz(user_id: int) -> int | None:
    """يرجع tz_offset بالدقائق، أو None إذا لم يُحدَّد بعد."""
    row = db_fetchone(
        "SELECT tz_offset FROM user_timezone WHERE user_id = %s",
        (user_id,)
    )
    return row["tz_offset"] if row else None


def set_user_tz(user_id: int, tz_offset: int) -> None:
    """يحفظ أو يُحدّث توقيت المستخدم (بالدقائق)."""
    db_execute(
        """
        INSERT INTO user_timezone (user_id, tz_offset, updated_at)
        VALUES (%s, %s, EXTRACT(EPOCH FROM NOW())::INTEGER)
        ON CONFLICT (user_id) DO UPDATE SET
            tz_offset  = EXCLUDED.tz_offset,
            updated_at = EXCLUDED.updated_at
        """,
        (user_id, tz_offset)
    )

"""
database/db_queries/quran_queries.py
──────────────────────────────────────
استعلامات جداول القرآن الكريم والختمة

Tables: suras, ayat, user_quran_progress, user_favorites,
        surah_read_progress, khatma_progress, khatma_goals,
        khatma_daily_log, khatma_streak, khatma_reminders,
        khatma_counted_ayat, khatma_achievements_seen
"""
from typing import Optional
from database.connection import get_db_conn

TOTAL_QURAN_AYAT = 6236

# أنواع التفسير المدعومة
TAFSEER_TYPES = {
    "المختصر": "tafseer_mukhtasar",
    "السعدي":  "tafseer_saadi",
    "الميسر":  "tafseer_muyassar",
}


# ══════════════════════════════════════════
# السور
# ══════════════════════════════════════════

def get_sura(sura_id: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM suras WHERE id = ?", (sura_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_sura_by_name(name: str) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM suras WHERE name = ?", (name,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_suras() -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM suras ORDER BY id ASC")
    return [dict(r) for r in cur.fetchall()]


def get_suras_with_ayat() -> list[dict]:
    """يرجع السور التي تحتوي على آية واحدة على الأقل."""
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT s.id, s.name, COUNT(a.id) AS ayah_count
        FROM suras s
        JOIN ayat a ON a.sura_id = s.id
        GROUP BY s.id
        ORDER BY s.id ASC
    """)
    return [dict(r) for r in cur.fetchall()]


def insert_sura(sura_id: int, name: str) -> None:
    """يُدرج سورة إذا لم تكن موجودة."""
    conn = get_db_conn()
    conn.execute(
        "INSERT OR IGNORE INTO suras (id, name) VALUES (?, ?)",
        (sura_id, name)
    )
    conn.commit()


# ══════════════════════════════════════════
# الآيات
# ══════════════════════════════════════════

def get_ayah(ayah_id: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id = ?
    """, (ayah_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_ayah_by_sura_number(sura_id: int, ayah_number: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id = ? AND a.ayah_number = ?
    """, (sura_id, ayah_number))
    row = cur.fetchone()
    return dict(row) if row else None


def get_first_ayah() -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        ORDER BY a.id ASC LIMIT 1
    """)
    row = cur.fetchone()
    return dict(row) if row else None


def get_next_ayah(current_id: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id > ? ORDER BY a.id ASC LIMIT 1
    """, (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_prev_ayah(current_id: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id < ? ORDER BY a.id DESC LIMIT 1
    """, (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_total_ayat() -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM ayat")
    return cur.fetchone()[0]


def get_ayat_by_sura(sura_id: int) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id = ? ORDER BY a.ayah_number ASC
    """, (sura_id,))
    return [dict(r) for r in cur.fetchall()]


def get_next_ayah_number_in_sura(sura_id: int) -> int:
    """يرجع رقم الآية التالية للإدراج في السورة (آخر رقم + 1)."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT MAX(ayah_number) FROM ayat WHERE sura_id = ?", (sura_id,))
    row = cur.fetchone()
    return (row[0] or 0) + 1


def get_next_tafseer_ayah(sura_id: int, tafseer_col: str) -> int:
    """
    يرجع رقم أول آية تحتاج تفسيراً في السورة.
    إذا كل الآيات لها تفسير → يرجع آخر رقم + 1.
    """
    cur = get_db_conn().cursor()
    cur.execute(
        f"SELECT ayah_number FROM ayat "
        f"WHERE sura_id = ? AND ({tafseer_col} IS NULL OR {tafseer_col} = '') "
        f"ORDER BY ayah_number ASC LIMIT 1",
        (sura_id,),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT MAX(ayah_number) FROM ayat WHERE sura_id = ?", (sura_id,))
    row = cur.fetchone()
    return (row[0] or 0) + 1


def search_ayat(normalized_query: str,
                word_boundary: bool = False) -> tuple[list[dict], int]:
    """
    يبحث في text_without_tashkeel.
    word_boundary=True → يطابق الكلمة كاملة فقط.
    يرجع (قائمة_الآيات, إجمالي_التكرارات).
    """
    cur = get_db_conn().cursor()

    if word_boundary:
        patterns = [
            f"% {normalized_query} %",
            f"{normalized_query} %",
            f"% {normalized_query}",
            normalized_query,
        ]
        placeholders = " OR ".join(["a.text_without_tashkeel LIKE ?"] * len(patterns))
        cur.execute(f"""
            SELECT a.*, s.name AS sura_name
            FROM ayat a JOIN suras s ON a.sura_id = s.id
            WHERE {placeholders}
            ORDER BY a.id ASC LIMIT 1000
        """, patterns)
    else:
        cur.execute("""
            SELECT a.*, s.name AS sura_name
            FROM ayat a JOIN suras s ON a.sura_id = s.id
            WHERE a.text_without_tashkeel LIKE ?
            ORDER BY a.id ASC LIMIT 1000
        """, (f"%{normalized_query}%",))

    rows = [dict(r) for r in cur.fetchall()]
    total_occurrences = sum(
        r["text_without_tashkeel"].count(normalized_query) for r in rows
    )
    return rows, total_occurrences


def insert_ayah(sura_id: int, ayah_number: int,
                text_with: str, text_without: str) -> int:
    """يُدرج آية جديدة. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO ayat
            (sura_id, ayah_number, text_with_tashkeel, text_without_tashkeel)
        VALUES (?, ?, ?, ?)
        """,
        (sura_id, ayah_number, text_with.strip(), text_without)
    )
    conn.commit()
    return cur.lastrowid or 0


def update_ayah_text(ayah_id: int, text_with: str, text_without: str) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE ayat SET text_with_tashkeel = ?, text_without_tashkeel = ? WHERE id = ?",
        (text_with.strip(), text_without, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    if tafseer_col not in TAFSEER_TYPES.values():
        return False
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        f"UPDATE ayat SET {tafseer_col} = ? WHERE id = ?",
        (content.strip(), ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_all_ayat() -> None:
    """يحذف جميع الآيات ويُعيد ضبط الـ autoincrement."""
    conn = get_db_conn()
    conn.execute("DELETE FROM ayat")
    conn.execute("DELETE FROM sqlite_sequence WHERE name='ayat'")
    conn.commit()


def renormalize_ayat(normalize_fn) -> int:
    """
    يُعيد تطبيع text_without_tashkeel لجميع الآيات.
    يرجع عدد الصفوف المُحدَّثة.
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id, text_without_tashkeel FROM ayat")
    rows    = cur.fetchall()
    updated = 0
    for row in rows:
        ayah_id  = row[0]
        old_text = row[1] or ""
        new_text = normalize_fn(old_text)
        if new_text != old_text:
            cur.execute(
                "UPDATE ayat SET text_without_tashkeel = ? WHERE id = ?",
                (new_text, ayah_id),
            )
            updated += 1
    if updated:
        conn.commit()
    return updated


# ══════════════════════════════════════════
# تقدم القراءة المتسلسلة
# ══════════════════════════════════════════

def get_quran_progress(user_id: int) -> Optional[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM user_quran_progress WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def save_quran_progress(user_id: int, ayah_id: int,
                        message_id: int = None) -> None:
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO user_quran_progress (user_id, last_ayah_id, message_id)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            last_ayah_id = excluded.last_ayah_id,
            message_id   = excluded.message_id
        """,
        (user_id, ayah_id, message_id)
    )
    conn.commit()


def reset_quran_progress(user_id: int) -> None:
    first    = get_first_ayah()
    first_id = first["id"] if first else 1
    save_quran_progress(user_id, first_id, None)


# ══════════════════════════════════════════
# تقدم قراءة السور
# ══════════════════════════════════════════

def get_surah_read_progress(user_id: int, surah_id: int) -> int:
    """يرجع آخر رقم آية قرأها المستخدم في السورة (1 إذا لم يبدأ)."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT ayah FROM surah_read_progress WHERE user_id = ? AND surah_id = ?",
        (user_id, surah_id),
    )
    row = cur.fetchone()
    return row[0] if row else 1


def save_surah_read_progress(user_id: int, surah_id: int,
                              ayah_number: int) -> None:
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO surah_read_progress (user_id, surah_id, ayah)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, surah_id) DO UPDATE SET ayah = excluded.ayah
        """,
        (user_id, surah_id, ayah_number),
    )
    conn.commit()


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def add_favorite(user_id: int, ayah_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO user_favorites (user_id, ayah_id) VALUES (?, ?)",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_favorite(user_id: int, ayah_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM user_favorites WHERE user_id = ? AND ayah_id = ?",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def is_favorite(user_id: int, ayah_id: int) -> bool:
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT 1 FROM user_favorites WHERE user_id = ? AND ayah_id = ?",
        (user_id, ayah_id),
    )
    return cur.fetchone() is not None


def get_favorites(user_id: int) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name AS sura_name
        FROM user_favorites f
        JOIN ayat a ON f.ayah_id = a.id
        JOIN suras s ON a.sura_id = s.id
        WHERE f.user_id = ?
        ORDER BY f.added_at ASC
    """, (user_id,))
    return [dict(r) for r in cur.fetchall()]


def clear_favorites(user_id: int) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM user_favorites WHERE user_id = ?", (user_id,))
    conn.commit()
    return cur.rowcount


# ══════════════════════════════════════════
# ختمة القرآن
# ══════════════════════════════════════════

def get_khatma(user_id: int) -> dict:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM khatma_progress WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else {
        "user_id": user_id, "last_surah": 1, "last_ayah": 1,
        "total_read": 0, "updated_at": None,
    }


def update_khatma(user_id: int, surah_id: int, ayah_number: int) -> bool:
    """
    يُحدّث تقدم الختمة ويحتسب الآية إذا لم تُحتسب اليوم.
    يرجع True إذا احتُسبت آية جديدة.
    """
    from datetime import date, timedelta
    today = date.today().isoformat()
    conn  = get_db_conn()
    cur   = conn.cursor()

    cur.execute(
        "SELECT id FROM ayat WHERE sura_id = ? AND ayah_number = ?",
        (surah_id, ayah_number),
    )
    row = cur.fetchone()
    if not row:
        return False
    ayah_id = row[0]

    # منع التكرار اليومي
    cur.execute(
        "SELECT 1 FROM khatma_counted_ayat WHERE user_id = ? AND ayah_id = ? AND log_date = ?",
        (user_id, ayah_id, today),
    )
    if cur.fetchone():
        conn.execute(
            """
            INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
            VALUES (?, ?, ?, 0, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                last_surah = excluded.last_surah,
                last_ayah  = excluded.last_ayah,
                updated_at = excluded.updated_at
            """,
            (user_id, surah_id, ayah_number),
        )
        conn.commit()
        return False

    conn.execute(
        "INSERT OR IGNORE INTO khatma_counted_ayat (user_id, ayah_id, log_date) VALUES (?, ?, ?)",
        (user_id, ayah_id, today),
    )
    conn.execute(
        """
        INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
        VALUES (?, ?, ?, 1, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            last_surah = excluded.last_surah,
            last_ayah  = excluded.last_ayah,
            total_read = total_read + 1,
            updated_at = excluded.updated_at
        """,
        (user_id, surah_id, ayah_number),
    )
    conn.execute(
        """
        INSERT INTO khatma_daily_log (user_id, log_date, count) VALUES (?, ?, 1)
        ON CONFLICT(user_id, log_date) DO UPDATE SET count = count + 1
        """,
        (user_id, today),
    )

    # تحديث الـ streak
    cur.execute(
        "SELECT current_streak, last_read_date FROM khatma_streak WHERE user_id = ?",
        (user_id,)
    )
    streak_row = cur.fetchone()
    yesterday  = (date.today() - timedelta(days=1)).isoformat()
    if streak_row:
        streak, last_date = streak_row[0], streak_row[1]
        if last_date == today:
            new_streak = streak
        elif last_date == yesterday:
            new_streak = streak + 1
        else:
            try:
                from datetime import datetime as _dt
                gap = (_dt.fromisoformat(today) - _dt.fromisoformat(last_date)).days
                new_streak = streak + 1 if gap <= 7 else 1
            except Exception:
                new_streak = 1
    else:
        new_streak = 1

    conn.execute(
        """
        INSERT INTO khatma_streak (user_id, current_streak, last_read_date)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            current_streak = excluded.current_streak,
            last_read_date = excluded.last_read_date
        """,
        (user_id, new_streak, today),
    )
    conn.commit()
    return True


def reset_khatma(user_id: int) -> None:
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
        VALUES (?, 1, 1, 0, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            last_surah = 1, last_ayah = 1, total_read = 0,
            updated_at = datetime('now')
        """,
        (user_id,),
    )
    conn.commit()


def get_khatma_goal(user_id: int) -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT daily_target FROM khatma_goals WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 10


def set_khatma_goal(user_id: int, target: int) -> None:
    conn = get_db_conn()
    conn.execute(
        """
        INSERT INTO khatma_goals (user_id, daily_target) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET daily_target = excluded.daily_target
        """,
        (user_id, target),
    )
    conn.commit()


def get_khatma_daily_avg(user_id: int, days: int = 3) -> int:
    """يرجع متوسط الآيات المقروءة يومياً خلال آخر N أيام."""
    from datetime import date, timedelta
    cur   = get_db_conn().cursor()
    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(1, days + 1)]
    placeholders = ",".join("?" * len(dates))
    cur.execute(
        f"SELECT SUM(count) FROM khatma_daily_log WHERE user_id = ? AND log_date IN ({placeholders})",
        [user_id] + dates,
    )
    total = cur.fetchone()[0] or 0
    return total // days


def get_khatma_streak(user_id: int) -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT current_streak FROM khatma_streak WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0


def get_khatma_today_count(user_id: int) -> int:
    from datetime import date
    today = date.today().isoformat()
    cur   = get_db_conn().cursor()
    cur.execute(
        "SELECT count FROM khatma_daily_log WHERE user_id = ? AND log_date = ?",
        (user_id, today),
    )
    row = cur.fetchone()
    return row[0] if row else 0


def get_khatma_best_day(user_id: int) -> int:
    cur = get_db_conn().cursor()
    cur.execute("SELECT MAX(count) FROM khatma_daily_log WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row and row[0] else 0


def get_days_since_last_read(user_id: int) -> int:
    from datetime import date, datetime
    cur = get_db_conn().cursor()
    cur.execute("SELECT last_read_date FROM khatma_streak WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return 999
    try:
        return (date.today() - datetime.fromisoformat(row[0]).date()).days
    except Exception:
        return 999


# ══════════════════════════════════════════
# تذكيرات الختمة
# ══════════════════════════════════════════

def get_khatma_reminders(user_id: int) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT * FROM khatma_reminders WHERE user_id = ? AND enabled = 1 ORDER BY hour, minute",
        (user_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def count_khatma_reminders(user_id: int) -> int:
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT COUNT(*) FROM khatma_reminders WHERE user_id = ? AND enabled = 1",
        (user_id,),
    )
    return cur.fetchone()[0]


def add_khatma_reminder(user_id: int, hour: int, minute: int,
                        tz_offset: int = 0) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO khatma_reminders (user_id, hour, minute, tz_offset) VALUES (?, ?, ?, ?)",
        (user_id, hour, minute, tz_offset),
    )
    conn.commit()
    return cur.lastrowid


def delete_khatma_reminder(reminder_id: int, user_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM khatma_reminders WHERE id = ? AND user_id = ?",
        (reminder_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_due_khatma_reminders(utc_hour: int, utc_minute: int) -> list[dict]:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM khatma_reminders WHERE enabled = 1")
    due = []
    for r in cur.fetchall():
        r = dict(r)
        local_total = r["hour"] * 60 + r["minute"]
        utc_total   = (local_total - r["tz_offset"]) % (24 * 60)
        if utc_total == utc_hour * 60 + utc_minute:
            due.append(r)
    return due


# ══════════════════════════════════════════
# إنجازات الختمة
# ══════════════════════════════════════════

_ACHIEVEMENTS = {
    "active_reader": {"total": 1000, "streak": None, "label": "قارئ نشيط 📖"},
    "week_streak":   {"total": None,  "streak": 7,   "label": "أسبوع متواصل 🔥"},
}


def check_new_achievements(user_id: int) -> list[str]:
    """يرجع قائمة الإنجازات المُفتَحة حديثاً ويُسجّلها كمشاهَدة."""
    k      = get_khatma(user_id)
    streak = get_khatma_streak(user_id)
    conn   = get_db_conn()
    cur    = conn.cursor()

    new_ones = []
    for key, cond in _ACHIEVEMENTS.items():
        cur.execute(
            "SELECT 1 FROM khatma_achievements_seen WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        if cur.fetchone():
            continue
        unlocked = (
            (cond["total"]  and k["total_read"] >= cond["total"]) or
            (cond["streak"] and streak >= cond["streak"])
        )
        if unlocked:
            conn.execute(
                "INSERT OR IGNORE INTO khatma_achievements_seen (user_id, key) VALUES (?, ?)",
                (user_id, key),
            )
            new_ones.append(cond["label"])

    if new_ones:
        conn.commit()
    return new_ones

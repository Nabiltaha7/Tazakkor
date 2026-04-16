"""
database/db_queries/quran_queries.py
──────────────────────────────────────
استعلامات جداول القرآن الكريم والختمة — PostgreSQL

Tables: suras, ayat, user_quran_progress, user_favorites,
        surah_read_progress, khatma_progress, khatma_goals,
        khatma_daily_log, khatma_streak, khatma_reminders,
        khatma_counted_ayat, khatma_achievements_seen
"""
from typing import Optional
from database.connection import get_db_conn, db_execute, db_fetchone, db_fetchall

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
    return db_fetchone("SELECT * FROM suras WHERE id = %s", (sura_id,))


def get_sura_by_name(name: str) -> Optional[dict]:
    return db_fetchone("SELECT * FROM suras WHERE name = %s", (name,))


def get_all_suras() -> list[dict]:
    return db_fetchall("SELECT * FROM suras ORDER BY id ASC")


def get_suras_with_ayat() -> list[dict]:
    """يرجع السور التي تحتوي على آية واحدة على الأقل."""
    return db_fetchall("""
        SELECT s.id, s.name, COUNT(a.id) AS ayah_count
        FROM suras s
        JOIN ayat a ON a.sura_id = s.id
        GROUP BY s.id
        ORDER BY s.id ASC
    """)


def insert_sura(sura_id: int, name: str) -> None:
    """يُدرج سورة إذا لم تكن موجودة."""
    db_execute(
        "INSERT INTO suras (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (sura_id, name)
    )


# ══════════════════════════════════════════
# الآيات
# ══════════════════════════════════════════

def get_ayah(ayah_id: int) -> Optional[dict]:
    return db_fetchone("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id = %s
    """, (ayah_id,))


def get_ayah_by_sura_number(sura_id: int, ayah_number: int) -> Optional[dict]:
    return db_fetchone("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id = %s AND a.ayah_number = %s
    """, (sura_id, ayah_number))


def get_first_ayah() -> Optional[dict]:
    return db_fetchone("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        ORDER BY a.id ASC LIMIT 1
    """)


def get_next_ayah(current_id: int) -> Optional[dict]:
    return db_fetchone("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id > %s ORDER BY a.id ASC LIMIT 1
    """, (current_id,))


def get_prev_ayah(current_id: int) -> Optional[dict]:
    return db_fetchone("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.id < %s ORDER BY a.id DESC LIMIT 1
    """, (current_id,))


def get_total_ayat() -> int:
    row = db_fetchone("SELECT COUNT(*) AS cnt FROM ayat")
    return row["cnt"] if row else 0


def get_ayat_by_sura(sura_id: int) -> list[dict]:
    return db_fetchall("""
        SELECT a.*, s.name AS sura_name
        FROM ayat a JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id = %s ORDER BY a.ayah_number ASC
    """, (sura_id,))


def get_next_ayah_number_in_sura(sura_id: int) -> int:
    """يرجع رقم الآية التالية للإدراج في السورة (آخر رقم + 1)."""
    row = db_fetchone("SELECT MAX(ayah_number) AS mx FROM ayat WHERE sura_id = %s", (sura_id,))
    return (row["mx"] or 0) + 1 if row else 1


def get_next_tafseer_ayah(sura_id: int, tafseer_col: str) -> int:
    """
    يرجع رقم أول آية تحتاج تفسيراً في السورة.
    إذا كل الآيات لها تفسير → يرجع آخر رقم + 1.
    """
    row = db_fetchone(
        f"SELECT ayah_number FROM ayat "
        f"WHERE sura_id = %s AND ({tafseer_col} IS NULL OR {tafseer_col} = '') "
        f"ORDER BY ayah_number ASC LIMIT 1",
        (sura_id,),
    )
    if row:
        return row["ayah_number"]
    row = db_fetchone("SELECT MAX(ayah_number) AS mx FROM ayat WHERE sura_id = %s", (sura_id,))
    return (row["mx"] or 0) + 1 if row else 1


def search_ayat(normalized_query: str,
                word_boundary: bool = False) -> tuple[list[dict], int]:
    """
    يبحث في text_without_tashkeel.
    word_boundary=True → يطابق الكلمة كاملة فقط.
    يرجع (قائمة_الآيات, إجمالي_التكرارات).
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        if word_boundary:
            patterns = [
                f"% {normalized_query} %",
                f"{normalized_query} %",
                f"% {normalized_query}",
                normalized_query,
            ]
            placeholders = " OR ".join(["a.text_without_tashkeel LIKE %s"] * len(patterns))
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
                WHERE a.text_without_tashkeel LIKE %s
                ORDER BY a.id ASC LIMIT 1000
            """, (f"%{normalized_query}%",))

        rows = [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()

    total_occurrences = sum(
        r["text_without_tashkeel"].count(normalized_query) for r in rows
    )
    return rows, total_occurrences


def insert_ayah(sura_id: int, ayah_number: int,
                text_with: str, text_without: str) -> int:
    """يُدرج آية جديدة. يرجع id الصف الجديد."""
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO ayat (sura_id, ayah_number, text_with_tashkeel, text_without_tashkeel)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (sura_id, ayah_number) DO NOTHING
            RETURNING id
            """,
            (sura_id, ayah_number, text_with.strip(), text_without)
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def update_ayah_text(ayah_id: int, text_with: str, text_without: str) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE ayat SET text_with_tashkeel = %s, text_without_tashkeel = %s WHERE id = %s",
            (text_with.strip(), text_without, ayah_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def update_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    if tafseer_col not in TAFSEER_TYPES.values():
        return False
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            f"UPDATE ayat SET {tafseer_col} = %s WHERE id = %s",
            (content.strip(), ayah_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def delete_all_ayat() -> None:
    """يحذف جميع الآيات ويُعيد ضبط التسلسل."""
    db_execute("DELETE FROM ayat")
    db_execute("ALTER SEQUENCE ayat_id_seq RESTART WITH 1")


def renormalize_ayat(normalize_fn) -> int:
    """
    يُعيد تطبيع text_without_tashkeel لجميع الآيات.
    يرجع عدد الصفوف المُحدَّثة.
    """
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT id, text_without_tashkeel FROM ayat")
        rows    = cur.fetchall()
        updated = 0
        for row in rows:
            ayah_id  = row["id"]
            old_text = row["text_without_tashkeel"] or ""
            new_text = normalize_fn(old_text)
            if new_text != old_text:
                cur.execute(
                    "UPDATE ayat SET text_without_tashkeel = %s WHERE id = %s",
                    (new_text, ayah_id),
                )
                updated += 1
        if updated:
            conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# ══════════════════════════════════════════
# تقدم القراءة المتسلسلة
# ══════════════════════════════════════════

def get_quran_progress(user_id: int) -> Optional[dict]:
    return db_fetchone("SELECT * FROM user_quran_progress WHERE user_id = %s", (user_id,))


def save_quran_progress(user_id: int, ayah_id: int,
                        message_id: int = None) -> None:
    db_execute(
        """
        INSERT INTO user_quran_progress (user_id, last_ayah_id, message_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            last_ayah_id = EXCLUDED.last_ayah_id,
            message_id   = EXCLUDED.message_id
        """,
        (user_id, ayah_id, message_id)
    )


def reset_quran_progress(user_id: int) -> None:
    first    = get_first_ayah()
    first_id = first["id"] if first else 1
    save_quran_progress(user_id, first_id, None)


# ══════════════════════════════════════════
# تقدم قراءة السور
# ══════════════════════════════════════════

def get_surah_read_progress(user_id: int, surah_id: int) -> int:
    """يرجع آخر رقم آية قرأها المستخدم في السورة (1 إذا لم يبدأ)."""
    row = db_fetchone(
        "SELECT ayah FROM surah_read_progress WHERE user_id = %s AND surah_id = %s",
        (user_id, surah_id),
    )
    return row["ayah"] if row else 1


def save_surah_read_progress(user_id: int, surah_id: int,
                              ayah_number: int) -> None:
    db_execute(
        """
        INSERT INTO surah_read_progress (user_id, surah_id, ayah)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, surah_id) DO UPDATE SET ayah = EXCLUDED.ayah
        """,
        (user_id, surah_id, ayah_number),
    )


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def add_favorite(user_id: int, ayah_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO user_favorites (user_id, ayah_id) VALUES (%s, %s) "
            "ON CONFLICT (user_id, ayah_id) DO NOTHING",
            (user_id, ayah_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def remove_favorite(user_id: int, ayah_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM user_favorites WHERE user_id = %s AND ayah_id = %s",
            (user_id, ayah_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def is_favorite(user_id: int, ayah_id: int) -> bool:
    return db_fetchone(
        "SELECT 1 AS found FROM user_favorites WHERE user_id = %s AND ayah_id = %s",
        (user_id, ayah_id),
    ) is not None


def get_favorites(user_id: int) -> list[dict]:
    return db_fetchall("""
        SELECT a.*, s.name AS sura_name
        FROM user_favorites f
        JOIN ayat a ON f.ayah_id = a.id
        JOIN suras s ON a.sura_id = s.id
        WHERE f.user_id = %s
        ORDER BY f.added_at ASC
    """, (user_id,))


def clear_favorites(user_id: int) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM user_favorites WHERE user_id = %s", (user_id,))
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# ══════════════════════════════════════════
# ختمة القرآن
# ══════════════════════════════════════════

def get_khatma(user_id: int) -> dict:
    row = db_fetchone("SELECT * FROM khatma_progress WHERE user_id = %s", (user_id,))
    return row if row else {
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

    try:
        cur.execute(
            "SELECT id FROM ayat WHERE sura_id = %s AND ayah_number = %s",
            (surah_id, ayah_number),
        )
        row = cur.fetchone()
        if not row:
            return False
        ayah_id = row["id"]

        # منع التكرار اليومي
        cur.execute(
            "SELECT 1 FROM khatma_counted_ayat "
            "WHERE user_id = %s AND ayah_id = %s AND log_date = %s",
            (user_id, ayah_id, today),
        )
        if cur.fetchone():
            cur.execute(
                """
                INSERT INTO khatma_progress
                    (user_id, last_surah, last_ayah, total_read, updated_at)
                VALUES (%s, %s, %s, 0, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    last_surah = EXCLUDED.last_surah,
                    last_ayah  = EXCLUDED.last_ayah,
                    updated_at = EXCLUDED.updated_at
                """,
                (user_id, surah_id, ayah_number),
            )
            conn.commit()
            return False

        cur.execute(
            "INSERT INTO khatma_counted_ayat (user_id, ayah_id, log_date) "
            "VALUES (%s, %s, %s) ON CONFLICT (user_id, ayah_id, log_date) DO NOTHING",
            (user_id, ayah_id, today),
        )
        cur.execute(
            """
            INSERT INTO khatma_progress
                (user_id, last_surah, last_ayah, total_read, updated_at)
            VALUES (%s, %s, %s, 1, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                last_surah = EXCLUDED.last_surah,
                last_ayah  = EXCLUDED.last_ayah,
                total_read = khatma_progress.total_read + 1,
                updated_at = EXCLUDED.updated_at
            """,
            (user_id, surah_id, ayah_number),
        )
        cur.execute(
            """
            INSERT INTO khatma_daily_log (user_id, log_date, count) VALUES (%s, %s, 1)
            ON CONFLICT (user_id, log_date) DO UPDATE
                SET count = khatma_daily_log.count + 1
            """,
            (user_id, today),
        )

        # تحديث الـ streak
        cur.execute(
            "SELECT current_streak, last_read_date FROM khatma_streak WHERE user_id = %s",
            (user_id,)
        )
        streak_row = cur.fetchone()
        yesterday  = (date.today() - timedelta(days=1)).isoformat()
        if streak_row:
            streak    = streak_row["current_streak"]
            last_date = streak_row["last_read_date"]
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

        cur.execute(
            """
            INSERT INTO khatma_streak (user_id, current_streak, last_read_date)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                current_streak = EXCLUDED.current_streak,
                last_read_date = EXCLUDED.last_read_date
            """,
            (user_id, new_streak, today),
        )
        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def reset_khatma(user_id: int) -> None:
    db_execute(
        """
        INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
        VALUES (%s, 1, 1, 0, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            last_surah = 1, last_ayah = 1, total_read = 0,
            updated_at = NOW()
        """,
        (user_id,),
    )


def get_khatma_goal(user_id: int) -> int:
    row = db_fetchone("SELECT daily_target FROM khatma_goals WHERE user_id = %s", (user_id,))
    return row["daily_target"] if row else 10


def set_khatma_goal(user_id: int, target: int) -> None:
    db_execute(
        """
        INSERT INTO khatma_goals (user_id, daily_target) VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET daily_target = EXCLUDED.daily_target
        """,
        (user_id, target),
    )


def get_khatma_daily_avg(user_id: int, days: int = 3) -> int:
    """يرجع متوسط الآيات المقروءة يومياً خلال آخر N أيام."""
    from datetime import date, timedelta
    dates        = [(date.today() - timedelta(days=i)).isoformat() for i in range(1, days + 1)]
    placeholders = ",".join(["%s"] * len(dates))
    row = db_fetchone(
        f"SELECT SUM(count) AS total FROM khatma_daily_log "
        f"WHERE user_id = %s AND log_date IN ({placeholders})",
        [user_id] + dates,
    )
    total = row["total"] or 0 if row else 0
    return total // days


def get_khatma_streak(user_id: int) -> int:
    row = db_fetchone(
        "SELECT current_streak FROM khatma_streak WHERE user_id = %s", (user_id,)
    )
    return row["current_streak"] if row else 0


def get_khatma_today_count(user_id: int) -> int:
    from datetime import date
    today = date.today().isoformat()
    row   = db_fetchone(
        "SELECT count FROM khatma_daily_log WHERE user_id = %s AND log_date = %s",
        (user_id, today),
    )
    return row["count"] if row else 0


def get_khatma_best_day(user_id: int) -> int:
    row = db_fetchone(
        "SELECT MAX(count) AS mx FROM khatma_daily_log WHERE user_id = %s", (user_id,)
    )
    return row["mx"] if row and row["mx"] else 0


def get_days_since_last_read(user_id: int) -> int:
    from datetime import date, datetime
    row = db_fetchone(
        "SELECT last_read_date FROM khatma_streak WHERE user_id = %s", (user_id,)
    )
    if not row or not row["last_read_date"]:
        return 999
    try:
        return (date.today() - datetime.fromisoformat(row["last_read_date"]).date()).days
    except Exception:
        return 999


# ══════════════════════════════════════════
# تذكيرات الختمة
# ══════════════════════════════════════════

def get_khatma_reminders(user_id: int) -> list[dict]:
    return db_fetchall(
        "SELECT * FROM khatma_reminders WHERE user_id = %s AND enabled = 1 "
        "ORDER BY hour, minute",
        (user_id,),
    )


def count_khatma_reminders(user_id: int) -> int:
    row = db_fetchone(
        "SELECT COUNT(*) AS cnt FROM khatma_reminders WHERE user_id = %s AND enabled = 1",
        (user_id,),
    )
    return row["cnt"] if row else 0


def add_khatma_reminder(user_id: int, hour: int, minute: int,
                        tz_offset: int = 0) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO khatma_reminders (user_id, hour, minute, tz_offset) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, hour, minute, tz_offset),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def delete_khatma_reminder(reminder_id: int, user_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM khatma_reminders WHERE id = %s AND user_id = %s",
            (reminder_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def get_due_khatma_reminders(utc_hour: int, utc_minute: int) -> list[dict]:
    rows = db_fetchall("SELECT * FROM khatma_reminders WHERE enabled = 1")
    due  = []
    for r in rows:
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
    try:
        for key, cond in _ACHIEVEMENTS.items():
            cur.execute(
                "SELECT 1 FROM khatma_achievements_seen WHERE user_id = %s AND key = %s",
                (user_id, key),
            )
            if cur.fetchone():
                continue
            unlocked = (
                (cond["total"]  and k["total_read"] >= cond["total"]) or
                (cond["streak"] and streak >= cond["streak"])
            )
            if unlocked:
                cur.execute(
                    "INSERT INTO khatma_achievements_seen (user_id, key) VALUES (%s, %s) "
                    "ON CONFLICT (user_id, key) DO NOTHING",
                    (user_id, key),
                )
                new_ones.append(cond["label"])

        if new_ones:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    return new_ones

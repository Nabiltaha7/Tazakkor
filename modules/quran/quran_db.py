"""
modules/quran/quran_db.py
──────────────────────────
Backward-compatible shim — يُحوِّل جميع الاستدعاءات إلى
database/db_queries/quran_queries.py

الكود الجديد يجب أن يستورد مباشرةً من:
    from database.db_queries.quran_queries import ...
"""
from database.db_queries.quran_queries import (
    TOTAL_QURAN_AYAT,
    TAFSEER_TYPES,
    # السور
    get_sura,
    get_sura_by_name,
    get_all_suras,
    get_suras_with_ayat,
    insert_sura,
    # الآيات
    get_ayah,
    get_ayah_by_sura_number,
    get_first_ayah,
    get_next_ayah,
    get_prev_ayah,
    get_total_ayat,
    get_ayat_by_sura,
    get_next_ayah_number_in_sura,
    get_next_tafseer_ayah,
    search_ayat,
    insert_ayah,
    update_ayah_text,
    update_tafseer,
    delete_all_ayat,
    renormalize_ayat,
    # تقدم القراءة المتسلسلة
    get_quran_progress  as get_progress,
    save_quran_progress as save_progress,
    reset_quran_progress as reset_progress,
    # تقدم قراءة السور
    get_surah_read_progress,
    save_surah_read_progress,
    # المفضلة
    add_favorite,
    remove_favorite,
    is_favorite,
    get_favorites,
    clear_favorites,
    # الختمة
    get_khatma,
    update_khatma,
    reset_khatma,
    get_khatma_goal,
    set_khatma_goal,
    get_khatma_daily_avg  as get_daily_avg,
    get_khatma_streak     as get_streak,
    get_khatma_today_count as get_today_count,
    get_khatma_best_day   as get_best_day,
    get_days_since_last_read,
    # تذكيرات الختمة
    get_khatma_reminders,
    count_khatma_reminders,
    add_khatma_reminder,
    delete_khatma_reminder,
    get_due_khatma_reminders,
    # الإنجازات
    check_new_achievements,
)

# ── ثوابت وأسماء السور (مُستخدَمة في seed وغيره) ──────────────────
BULK_SEPARATOR = "---"

SURAS_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه",
    "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم",
    "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر",
    "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق",
    "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة",
    "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس",
    "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد",
    "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات",
    "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر",
    "المسد", "الإخلاص", "الفلق", "الناس",
]


def auto_insert_suras() -> None:
    """يُدرج جميع السور تلقائياً إذا لم تكن موجودة."""
    for i, name in enumerate(SURAS_NAMES, 1):
        insert_sura(i, name)


def create_tables() -> None:
    """No-op — tables are created by database.init_db.init_db()."""
    pass


# ══════════════════════════════════════════
# إعادة تحميل الآيات من API
# ══════════════════════════════════════════

_QURAN_API_BASE = "https://api.alquran.cloud/v1/surah"


def _fetch_with_retry(url: str, retries: int = 3, delay: float = 2.0) -> dict:
    import time
    import urllib.request
    import json as _json

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return _json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError(f"فشل الاتصال بـ API بعد {retries} محاولات: {last_err}")


def _fetch_surah(surah_id: int) -> list[dict]:
    url  = f"{_QURAN_API_BASE}/{surah_id}"
    data = _fetch_with_retry(url)
    if data.get("code") != 200:
        raise RuntimeError(f"API أعاد كود غير متوقع للسورة {surah_id}: {data.get('code')}")
    ayahs = data.get("data", {}).get("ayahs")
    if not ayahs:
        raise RuntimeError(f"لا توجد آيات في استجابة API للسورة {surah_id}")
    return ayahs


def reload_ayat_from_api(progress_callback=None) -> tuple[bool, str]:
    """
    يحذف جميع الآيات ويعيد تحميلها من alquran.cloud API.

    الخطوات:
      1. تأكد من وجود جميع السور الـ 114 في جدول suras (أدرج المفقودة تلقائياً)
      2. احذف جميع الآيات الحالية
      3. حمّل آيات كل سورة من API بشكل مستقل
         — فشل سورة واحدة لا يوقف العملية كلها
      4. أعد تطبيع النص بعد الانتهاء

    يرجع (True, summary) أو (False, error_message).
    """
    from modules.quran.quran_service import normalize_arabic
    from database.connection import get_db_conn

    def _log(msg: str):
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    conn = get_db_conn()
    cur  = conn.cursor()

    # ── الخطوة 1: ضمان وجود جميع السور ──────────────────────────
    _log("🔍 التحقق من جدول السور...")
    cur.execute("SELECT COUNT(*) AS cnt FROM suras")
    sura_count = cur.fetchone()["cnt"]

    if sura_count < 114:
        _log(f"⚠️ جدول suras يحتوي على {sura_count} سورة فقط — سيتم إدراج المفقودة...")
        for i, name in enumerate(SURAS_NAMES, 1):
            cur.execute(
                "INSERT INTO suras (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (i, name)
            )
        conn.commit()
        cur.execute("SELECT COUNT(*) AS cnt FROM suras")
        sura_count = cur.fetchone()["cnt"]
        _log(f"✅ جدول suras يحتوي الآن على {sura_count} سورة.")
    else:
        _log(f"✅ جدول suras مكتمل ({sura_count} سورة).")

    # ── الخطوة 2: حذف جميع الآيات ───────────────────────────────
    _log("🗑 حذف الآيات القديمة...")
    try:
        cur.execute("DELETE FROM ayat")
        cur.execute("ALTER SEQUENCE ayat_id_seq RESTART WITH 1")
        conn.commit()
    except Exception as e:
        conn.rollback()
        return False, f"❌ فشل حذف الآيات القديمة:\n<code>{e}</code>"

    # ── الخطوة 3: تحميل الآيات سورة بسورة ───────────────────────
    total_inserted = 0
    skipped_suras  = []   # سور فشل تحميلها
    mismatches     = []   # سور بها تباين في العدد

    for sura_id in range(1, 115):
        # جلب اسم السورة (مضمون الوجود بعد الخطوة 1)
        cur.execute("SELECT name FROM suras WHERE id = %s", (sura_id,))
        row = cur.fetchone()
        sura_name = row["name"] if row else SURAS_NAMES[sura_id - 1]

        _log(f"📥 جاري تحميل سورة {sura_id}: {sura_name}...")

        # جلب الآيات من API — فشل سورة واحدة لا يوقف الكل
        try:
            ayahs = _fetch_surah(sura_id)
        except Exception as e:
            warn = f"⚠️ تخطي سورة {sura_id} ({sura_name}): {e}"
            skipped_suras.append(warn)
            _log(warn)
            continue

        ayahs.sort(key=lambda a: a["numberInSurah"])

        # إدراج آيات السورة في transaction مستقلة
        try:
            for ayah in ayahs:
                ayah_num     = int(ayah["numberInSurah"])
                text_with    = str(ayah["text"]).strip()
                text_without = normalize_arabic(text_with)
                cur.execute(
                    """
                    INSERT INTO ayat
                        (sura_id, ayah_number, text_with_tashkeel, text_without_tashkeel,
                         tafseer_mukhtasar, tafseer_saadi, tafseer_muyassar)
                    VALUES (%s, %s, %s, %s, NULL, NULL, NULL)
                    ON CONFLICT (sura_id, ayah_number) DO NOTHING
                    """,
                    (sura_id, ayah_num, text_with, text_without)
                )
            conn.commit()
        except Exception as e:
            warn = f"⚠️ خطأ في إدراج آيات سورة {sura_id} ({sura_name}): {e}"
            skipped_suras.append(warn)
            _log(warn)
            # تراجع عن آيات هذه السورة فقط
            try:
                cur.execute("DELETE FROM ayat WHERE sura_id = %s", (sura_id,))
                conn.commit()
            except Exception:
                pass
            continue

        inserted_count = len(ayahs)
        total_inserted += inserted_count

        # التحقق من العدد
        cur.execute("SELECT COUNT(*) AS cnt FROM ayat WHERE sura_id = %s", (sura_id,))
        db_count = cur.fetchone()["cnt"]
        if db_count != inserted_count:
            msg = f"⚠️ السورة {sura_id}: متوقع {inserted_count} آية، أُدرج {db_count}"
            mismatches.append(msg)
            _log(msg)
        else:
            _log(f"✅ سورة {sura_id} ({sura_name}): {inserted_count} آية")

    # ── الخطوة 4: ملخص النتيجة ───────────────────────────────────
    success = len(skipped_suras) == 0

    summary = (
        f"{'✅' if success else '⚠️'} اكتملت عملية إعادة التحميل\n\n"
        f"📊 إجمالي الآيات المُدرجة: <b>{total_inserted:,}</b>\n"
        f"📖 السور المُعالَجة: <b>{114 - len(skipped_suras)}</b> / 114"
    )
    if skipped_suras:
        summary += f"\n\n❌ سور فشل تحميلها ({len(skipped_suras)}):\n" + "\n".join(skipped_suras)
    if mismatches:
        summary += f"\n\n⚠️ تباينات في العدد ({len(mismatches)}):\n" + "\n".join(mismatches)

    return True, summary

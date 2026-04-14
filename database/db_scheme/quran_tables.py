"""
database/db_scheme/quran_tables.py
────────────────────────────────────
جداول القرآن الكريم والختمة

Tables:
  - suras                    : أسماء السور (114 سورة)
  - ayat                     : الآيات مع التشكيل والتفسير
  - user_quran_progress      : تقدم قراءة المستخدم (آية بآية)
  - user_favorites           : الآيات المفضلة لكل مستخدم
  - surah_read_progress      : تقدم قراءة كل سورة على حدة
  - khatma_progress          : تقدم ختمة القرآن
  - khatma_goals             : الهدف اليومي لكل مستخدم
  - khatma_daily_log         : سجل القراءة اليومي
  - khatma_streak            : سلسلة الاستمرارية في القراءة
  - khatma_reminders         : تذكيرات الختمة
  - khatma_counted_ayat      : منع تكرار احتساب الآية في نفس اليوم
  - khatma_achievements_seen : الإنجازات التي شاهدها المستخدم
"""

from database.connection import get_db_conn


def create_quran_tables() -> None:
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────
    # TABLE: suras
    # PURPOSE: أسماء السور الـ 114 — تُملأ تلقائياً عند التهيئة.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suras (
        id   INTEGER PRIMARY KEY,
        name TEXT    NOT NULL UNIQUE
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: ayat
    # PURPOSE: يخزّن جميع آيات القرآن مع نصين (بتشكيل وبدونه)
    #          وثلاثة تفاسير اختيارية.
    #
    # COLUMNS:
    #   sura_id               — يشير إلى suras.id.
    #   ayah_number           — رقم الآية داخل السورة.
    #   text_with_tashkeel    — النص الكامل بالتشكيل.
    #   text_without_tashkeel — النص المُطبَّع بدون تشكيل (للبحث).
    #   tafseer_*             — تفاسير اختيارية (مختصر / سعدي / ميسر).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ayat (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        sura_id               INTEGER NOT NULL,
        ayah_number           INTEGER NOT NULL,
        text_with_tashkeel    TEXT    NOT NULL,
        text_without_tashkeel TEXT    NOT NULL,
        tafseer_mukhtasar     TEXT    DEFAULT NULL,
        tafseer_saadi         TEXT    DEFAULT NULL,
        tafseer_muyassar      TEXT    DEFAULT NULL,
        UNIQUE (sura_id, ayah_number),
        FOREIGN KEY (sura_id) REFERENCES suras(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ayat_sura   ON ayat(sura_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ayat_search ON ayat(text_without_tashkeel)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: user_quran_progress
    # PURPOSE: يحفظ آخر آية وصل إليها المستخدم في وضع القراءة
    #          المتسلسلة (آية بآية عبر كامل القرآن).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_quran_progress (
        user_id      INTEGER PRIMARY KEY,
        last_ayah_id INTEGER NOT NULL DEFAULT 1,
        message_id   INTEGER DEFAULT NULL
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: user_favorites
    # PURPOSE: الآيات التي أضافها المستخدم إلى مفضلته.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_favorites (
        user_id  INTEGER NOT NULL,
        ayah_id  INTEGER NOT NULL,
        added_at INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (user_id, ayah_id),
        FOREIGN KEY (ayah_id) REFERENCES ayat(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: surah_read_progress
    # PURPOSE: يحفظ آخر آية قرأها المستخدم في كل سورة بشكل مستقل
    #          (وضع قراءة السورة المحددة).
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS surah_read_progress (
        user_id  INTEGER NOT NULL,
        surah_id INTEGER NOT NULL,
        ayah     INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (user_id, surah_id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_surah_progress_user ON surah_read_progress(user_id)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_progress
    # PURPOSE: يتتبع تقدم ختمة القرآن لكل مستخدم.
    #
    # COLUMNS:
    #   last_surah  — رقم آخر سورة وصل إليها.
    #   last_ayah   — رقم آخر آية وصل إليها.
    #   total_read  — إجمالي الآيات المقروءة (بدون تكرار يومي).
    #   updated_at  — وقت آخر تحديث.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_progress (
        user_id    INTEGER PRIMARY KEY,
        last_surah INTEGER NOT NULL DEFAULT 1,
        last_ayah  INTEGER NOT NULL DEFAULT 1,
        total_read INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_goals
    # PURPOSE: الهدف اليومي لعدد الآيات لكل مستخدم.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_goals (
        user_id      INTEGER PRIMARY KEY,
        daily_target INTEGER NOT NULL DEFAULT 10
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_daily_log
    # PURPOSE: سجل يومي لعدد الآيات المقروءة — يُستخدم للاقتراح
    #          الذكي وحساب المتوسط.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_daily_log (
        user_id  INTEGER NOT NULL,
        log_date TEXT    NOT NULL,
        count    INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, log_date)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_streak
    # PURPOSE: يتتبع سلسلة الأيام المتواصلة في قراءة الختمة.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_streak (
        user_id        INTEGER PRIMARY KEY,
        current_streak INTEGER NOT NULL DEFAULT 0,
        last_read_date TEXT
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_reminders
    # PURPOSE: تذكيرات الختمة اليومية المجدولة.
    #
    # COLUMNS:
    #   hour      — الساعة المحلية (0–23).
    #   minute    — الدقيقة المحلية (0–59).
    #   tz_offset — إزاحة UTC بالدقائق (مخزّنة هنا للأداء).
    #   enabled   — 1 مفعّل، 0 معطّل.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_reminders (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id   INTEGER NOT NULL,
        hour      INTEGER NOT NULL,
        minute    INTEGER NOT NULL,
        tz_offset INTEGER NOT NULL DEFAULT 0,
        enabled   INTEGER NOT NULL DEFAULT 1
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_khatma_reminders_user ON khatma_reminders(user_id)")

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_counted_ayat
    # PURPOSE: يمنع احتساب نفس الآية أكثر من مرة في اليوم الواحد.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_counted_ayat (
        user_id  INTEGER NOT NULL,
        ayah_id  INTEGER NOT NULL,
        log_date TEXT    NOT NULL,
        PRIMARY KEY (user_id, ayah_id, log_date)
    )
    """)

    # ──────────────────────────────────────────────────────────────
    # TABLE: khatma_achievements_seen
    # PURPOSE: يسجّل الإنجازات التي شاهدها المستخدم حتى لا تظهر مجدداً.
    # ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS khatma_achievements_seen (
        user_id INTEGER NOT NULL,
        key     TEXT    NOT NULL,
        PRIMARY KEY (user_id, key)
    )
    """)

    conn.commit()

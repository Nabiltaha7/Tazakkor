"""
منطق أعمال نظام القرآن — بدون تفاعل مع البوت
"""
import re
from typing import Optional
from modules.quran import quran_db as db

# ══════════════════════════════════════════
# تطبيع النص العربي
# ══════════════════════════════════════════

# التشكيل الأساسي: فتحة، ضمة، كسرة، تنوين، شدة، سكون، مد، طولة
_TASHKEEL = re.compile(
    r'['
    r'\u0610-\u061A'   # علامات قرآنية (صلى، قلى، إلخ)
    r'\u064B-\u065F'   # تشكيل كامل (تنوين، حركات، شدة، سكون...)
    r'\u0670'          # ألف خنجرية
    r'\u0640'          # طولة (tatweel)
    r'\u06D6-\u06DC'   # علامات وقف قرآنية (ۖ ۗ ۘ ۙ ۚ ۛ ۜ)
    r'\u06DF-\u06E4'   # علامات قرآنية إضافية (ۡ ۢ ۣ ۤ)
    r'\u06E7-\u06E8'   # علامات مد (ۧ ۨ)
    r'\u06EA-\u06ED'   # علامات وقف إضافية (۪ ۫ ۬ ۭ)
    r']'
)

# أشكال الألف المختلفة → ا
_ALEF_VARIANTS = re.compile(r'[أإآٱ\u0671]')
# تاء مربوطة → هاء
_TA_MARBUTA    = re.compile(r'ة')
# ألف مقصورة → ياء
_ALEF_MAQSURA  = re.compile(r'ى')
# واو همزة → واو
_WAW_HAMZA     = re.compile(r'ؤ')
# ياء همزة → ياء
_YA_HAMZA      = re.compile(r'ئ')


def remove_tashkeel(text: str) -> str:
    if not text:
        return text
    return _TASHKEEL.sub('', text)


def normalize_arabic(text: str) -> str:
    """
    تطبيع شامل للنص العربي:
    - إزالة التشكيل والرموز القرآنية الخاصة (وقف، مد، إلخ)
    - توحيد أشكال الألف (أ إ آ ٱ → ا)
    - توحيد التاء المربوطة (ة → ه)
    - توحيد الألف المقصورة (ى → ي)
    - توحيد واو الهمزة (ؤ → و)
    - توحيد ياء الهمزة (ئ → ي)
    - ضغط المسافات الزائدة
    """
    if not text:
        return text
    text = remove_tashkeel(text)
    text = _ALEF_VARIANTS.sub('ا', text)
    text = _TA_MARBUTA.sub('ه', text)
    text = _ALEF_MAQSURA.sub('ي', text)
    text = _WAW_HAMZA.sub('و', text)
    text = _YA_HAMZA.sub('ي', text)
    return ' '.join(text.split())


def normalize_text(text: str) -> str:
    """للتوافق مع الكود القديم — يستخدم normalize_arabic داخلياً."""
    return normalize_arabic(text).strip().lower()


# ══════════════════════════════════════════
# التلاوة
# ══════════════════════════════════════════

def get_current_ayah(user_id: int) -> Optional[dict]:
    """يرجع الآية الحالية للمستخدم (أو الأولى إذا لم يبدأ بعد)."""
    progress = db.get_progress(user_id)
    if progress:
        ayah = db.get_ayah(progress["last_ayah_id"])
        return ayah
    # لا يوجد تقدم — ابدأ من الأولى
    return db.get_first_ayah()


def navigate(user_id: int, direction: str) -> Optional[dict]:
    """
    direction: 'next' | 'prev'
    يرجع الآية الجديدة أو None إذا لم توجد.
    """
    progress = db.get_progress(user_id)
    current_id = progress["last_ayah_id"] if progress else (
        db.get_first_ayah() or {"id": 0}
    )["id"]

    if direction == "next":
        ayah = db.get_next_ayah(current_id)
    else:
        ayah = db.get_prev_ayah(current_id)

    return ayah


def save_position(user_id: int, ayah_id: int, message_id: int = None):
    db.save_progress(user_id, ayah_id, message_id)


def reset_user(user_id: int):
    db.reset_progress(user_id)


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def toggle_favorite(user_id: int, ayah_id: int) -> tuple[bool, str]:
    """
    يضيف أو يزيل من المفضلة.
    يرجع (is_now_favorite, message)
    """
    if db.is_favorite(user_id, ayah_id):
        db.remove_favorite(user_id, ayah_id)
        return False, "تمت إزالة الآية من المفضلة."
    else:
        db.add_favorite(user_id, ayah_id)
        return True, "تمت إضافة الآية إلى المفضلة ⭐️"


def get_user_favorites(user_id: int) -> list[dict]:
    return db.get_favorites(user_id)


# ══════════════════════════════════════════
# البحث
# ══════════════════════════════════════════

def search(query: str) -> tuple[list[dict], int]:
    """
    يبحث بعد تطبيع النص.
    يرجع (results, total_occurrences)

    - query بدون مسافة نهائية → بحث جزئي (LIKE %كلمة%)
    - query بمسافة نهائية     → بحث بحدود الكلمة (لا يطابق وقالوا)
    """
    # حذف كلمة "آية" من بداية الاستعلام إذا وُجدت
    q = query
    if q.lstrip().startswith("آية "):
        q = q.lstrip()[4:]

    # هل المستخدم أضاف مسافة نهائية قصداً؟
    word_boundary = q.endswith(" ")

    normalized = normalize_arabic(q)   # normalize يضغط المسافات تلقائياً
    if len(normalized) < 2:
        return [], 0

    results, total = db.search_ayat(normalized, word_boundary=word_boundary)
    return results, total


# ══════════════════════════════════════════
# التفسير
# ══════════════════════════════════════════

def get_available_tafseer(ayah: dict) -> list[tuple[str, str]]:
    """
    يرجع قائمة التفاسير المتاحة للآية.
    كل عنصر: (اسم_عربي, اسم_العمود)
    """
    available = []
    for name_ar, col in db.TAFSEER_TYPES.items():
        if ayah.get(col):
            available.append((name_ar, col))
    return available


# ══════════════════════════════════════════
# إدارة المحتوى (للمطورين)
# ══════════════════════════════════════════

def add_ayah(sura_name: str, ayah_number: int, text_with: str) -> int:
    sura = db.get_sura_by_name(sura_name)
    if not sura:
        return 0
    text_without = normalize_arabic(text_with)
    return db.insert_ayah(sura["id"], ayah_number, text_with, text_without)


def edit_ayah(ayah_id: int, new_text: str) -> bool:
    text_without = normalize_arabic(new_text)
    return db.update_ayah_text(ayah_id, new_text, text_without)


def edit_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    return db.update_tafseer(ayah_id, tafseer_col, content)


def bulk_add_ayat(sura_name: str, start_number: int, raw_text: str) -> int:
    """
    يضيف آيات متعددة مفصولة بـ BULK_SEPARATOR.
    إذا start_number=0 → يحدد تلقائياً من آخر آية موجودة + 1
    يرجع عدد الآيات المضافة.
    """
    sura = db.get_sura_by_name(sura_name)
    if not sura:
        return 0

    if start_number <= 0:
        start_number = db.get_next_ayah_number(sura["id"])

    items = [i.strip() for i in raw_text.split(db.BULK_SEPARATOR) if i.strip()]
    added = 0
    for i, text in enumerate(items):
        ayah_num = start_number + i
        result   = add_ayah(sura_name, ayah_num, text)
        if result:
            added += 1
    return added


# ══════════════════════════════════════════
# التحقق من صحة البيانات
# ══════════════════════════════════════════

def validate_sura_ayah(sura_name: str, ayah_number: int) -> tuple[bool, str, dict]:
    """
    يتحقق من وجود السورة والآية.
    يرجع (صحيح, رسالة_خطأ, بيانات_السورة_أو_الآية)
    """
    sura = db.get_sura_by_name(sura_name)
    if not sura:
        return False, f"❌ السورة '{sura_name}' غير موجودة.", {}

    ayah = db.get_ayah_by_sura_number(sura["id"], ayah_number)
    if not ayah:
        return False, f"❌ الآية {ayah_number} غير موجودة في سورة {sura_name}.", sura

    return True, "", ayah


def parse_sura_ayah_input(input_text: str) -> tuple[str, int]:
    """
    يحلل إدخال مثل "الفاتحة 1" إلى (اسم_السورة, رقم_الآية)
    """
    parts = input_text.strip().split()
    if len(parts) < 2:
        raise ValueError("الصيغة غير صحيحة. استخدم: سورة رقم_آية")

    try:
        ayah_num = int(parts[-1])
        sura_name = " ".join(parts[:-1])
        return sura_name, ayah_num
    except ValueError:
        raise ValueError("رقم الآية يجب أن يكون رقماً صحيحاً.")


# ══════════════════════════════════════════
# إدارة التفسير الجديدة
# ══════════════════════════════════════════

def add_single_tafseer(sura_name: str, ayah_number: int, tafseer_parts: list[str]) -> tuple[bool, str]:
    """
    إضافة تفسير واحد لآية معينة.
    tafseer_parts: [mukhtasar, muyassar, saadi] - يمكن أن تكون فارغة
    """
    valid, error_msg, ayah = validate_sura_ayah(sura_name, ayah_number)
    if not valid:
        return False, error_msg

    tafseer_cols = ["tafseer_mukhtasar", "tafseer_muyassar", "tafseer_saadi"]
    updated = 0

    for i, content in enumerate(tafseer_parts[:3]):  # أقصى 3 تفاسير
        if content.strip():
            col = tafseer_cols[i]
            if db.update_tafseer(ayah["id"], col, content.strip()):
                updated += 1

    return True, f"✅ تم تحديث {updated} تفسير لسورة {sura_name} آية {ayah_number}"


def add_bulk_tafseer(sura_name: str, tafseer_type: str, start_ayah: int, tafseer_parts: list[str]) -> tuple[bool, str]:
    """
    إضافة تفسير متعدد لسورة معينة بدءاً من آية محددة.
    """
    sura = db.get_sura_by_name(sura_name)
    if not sura:
        return False, f"❌ السورة '{sura_name}' غير موجودة."

    if tafseer_type not in db.TAFSEER_TYPES:
        return False, f"❌ نوع التفسير '{tafseer_type}' غير مدعوم."

    col = db.TAFSEER_TYPES[tafseer_type]
    updated = 0
    current_ayah = start_ayah

    for content in tafseer_parts:
        if content.strip():
            ayah = db.get_ayah_by_sura_number(sura["id"], current_ayah)
            if not ayah:
                break  # توقف إذا لم توجد الآية

            if db.update_tafseer(ayah["id"], col, content.strip()):
                updated += 1

            current_ayah += 1

    return True, f"✅ تم تحديث {updated} تفسير {tafseer_type} لسورة {sura_name} بدءاً من آية {start_ayah}"

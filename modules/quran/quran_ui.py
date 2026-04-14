"""
مساعدات واجهة المستخدم للقرآن — بناء النصوص والأزرار فقط
"""
from utils.pagination import btn, paginate_list
from modules.quran.quran_service import get_available_tafseer
from modules.quran import quran_db as db
from utils.helpers import get_lines, format_ayah_number

_B = "p"   # أزرق
_G = "su"  # أخضر
_R = "d"   # أحمر


def build_ayah_text(ayah: dict, total: int) -> str:
    """يبني نص عرض الآية."""

    sura = db.get_sura(ayah["sura_id"])
    sura_name = sura["name"] if sura else f"سورة {ayah['sura_id']}"
    
    return (
        f"📖 <b>{sura_name}</b>\n"
        f"‏━━━━━━━━\n\n"
        f"{ayah['text_with_tashkeel']} {format_ayah_number(ayah['ayah_number'])}\n\n"
        f"‏━━━━━━━━━━\n"
        f"<tg-spoiler><i>آية {ayah['id']} من {total}</i></tg-spoiler>"
    )

def build_ayah_buttons(uid: int, cid: int, ayah: dict,
                       is_fav: bool, has_prev: bool, has_next: bool,
                       source: str = None, fav_page: int = 0) -> tuple[list, list]:
    """يبني أزرار عرض الآية."""
    owner = (uid, cid)
    aid   = ayah["id"]

    # بيانات السياق لتمريرها لأزرار التنقل
    ctx = {"aid": aid}
    if source:
        ctx["src"] = source
        ctx["fp"]  = fav_page

    nav = []
    if has_next:
        nav.append(btn("⬅️ التالية", "qr_next", ctx, color=_B, owner=owner))
    if has_prev:
        nav.append(btn("➡️ السابقة", "qr_prev", ctx, color=_B, owner=owner))

    fav_label = "💛 إزالة من المفضلة" if is_fav else "⭐️ المفضلة"
    fav_ctx   = {"aid": aid}
    if source:
        fav_ctx["src"] = source
        fav_ctx["fp"]  = fav_page

    action_row = [
        btn("📖 تفسير", "qr_tafseer", {"aid": aid, **({"src": source, "fp": fav_page} if source else {})}, color=_B, owner=owner),
        btn(fav_label,  "qr_fav",     fav_ctx,                                                              color=_G, owner=owner),
        btn("❌ إغلاق", "qr_close",   {},                                                                   color=_R, owner=owner),
    ]

    buttons = nav + action_row
    layout  = ([len(nav)] if nav else []) + [3]

    # زر الرجوع للمفضلة — فقط إذا جاء المستخدم من المفضلة
    if source == "favorites":
        buttons.append(btn("⬅️ رجوع للمفضلة", "qr_back_favorites",
                           {"fp": fav_page}, color=_G, owner=owner))
        layout.append(1)

    return buttons, layout


def build_tafseer_buttons(uid: int, cid: int, ayah: dict,
                          source: str = None, fav_page: int = 0) -> tuple[list, list]:
    """يبني أزرار اختيار التفسير."""
    owner     = (uid, cid)
    aid       = ayah["id"]
    available = get_available_tafseer(ayah)

    if not available:
        return [], []

    tafseer_buttons = [
        btn(name_ar, "qr_show_tafseer",
            {"aid": aid, "col": col, **({"src": source, "fp": fav_page} if source else {})},
            color=_B, owner=owner)
        for name_ar, col in available
    ]

    back_ctx = {"aid": aid}
    if source:
        back_ctx["src"] = source
        back_ctx["fp"]  = fav_page

    back_btn = btn("🔙 رجوع", "qr_back_to_ayah", back_ctx, color=_R, owner=owner)

    buttons = tafseer_buttons + [back_btn]
    n = len(tafseer_buttons)

    if n >= 3:
        layout = [3] + ([n - 3] if n > 3 else []) + [1]
    else:
        layout = [n] + [1]

    return buttons, layout

def build_search_result_text(results: list[dict], page: int, total_pages: int,
                             query: str = "", ayat_count: int = 0,
                             total_occurrences: int = 0) -> str:
    """يبني نص نتائج البحث مع إحصائيات."""
    text = (
        f"🔎 <b>نتائج البحث عن:</b> «{query}»\n"
        f"📊 وُجد في <b>{ayat_count}</b> آية "
        f"(<b>{total_occurrences}</b> تكرار إجمالي)\n"
        f"{get_lines()}\n\n"
    )
    for r in results:
        sura = db.get_sura(r["sura_id"])
        sura_name = sura["name"] if sura else f"سورة {r['sura_id']}"
        text += (
            f"📖 <b>{sura_name}</b>\n\n"
            f"{r['text_with_tashkeel']} {format_ayah_number(r['ayah_number'])}\n\n"
        )
    if total_pages > 1:
        text += f"<i>صفحة {page+1} من {total_pages}</i>"
    return text


def build_search_buttons(uid: int, cid: int, query: str,
                         page: int, total_pages: int,
                         results: list[dict]) -> tuple[list, list]:
    """يبني أزرار نتائج البحث."""
    owner   = (uid, cid)
    buttons = []

    # أزرار النتائج
    for r in results:
        buttons.append(btn(
            f"📖 {r['sura_name']} {format_ayah_number(r['ayah_number'])}",
            "qr_goto_ayah",
            {"aid": r["id"], "src": "search"},
            color=_B, owner=owner,
        ))

    # أزرار التنقل
    nav = []

    if page < total_pages - 1:
        nav.append(btn("◀️", "qr_search_page",
                       {"q": query, "p": page + 1}, color=_G,owner=owner))

    nav.append(btn("❌ إغلاق", "qr_close", {}, color=_R, owner=owner))

    if page > 0:
        nav.append(btn("▶️", "qr_search_page",
                       {"q": query, "p": page - 1}, color=_G,owner=owner))
    buttons += nav

    # --- layout ---
    n_results = len(results)

    rows = n_results // 3
    remainder = n_results % 3

    layout = [3] * rows
    if remainder:
        layout.append(remainder)

    # صف التنقل
    if nav:
        layout.append(len(nav))

    return buttons, layout

def build_favorites_text(favs: list[dict], page: int, total_pages: int) -> str:

    text = f"⭐️ <b>مفضلتي</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    for f in favs:
        sura = db.get_sura(f["sura_id"])
        sura_name = sura["name"] if sura else f"سورة {f['sura_id']}"
        text += (
            f"📖 <b>{sura_name}</b>\n\n"
            f"{f['text_with_tashkeel']} {format_ayah_number(f['ayah_number'])}\n\n"
        )
    return text

def build_favorites_buttons(uid: int, cid: int, favs: list[dict],
                             page: int, total_pages: int) -> tuple[list, list]:
    owner = (uid, cid)

    buttons = []
    row = []

    # --- أزرار المفضلة (3 في الصف مع RTL) ---
    for f in favs:
        row.append(
            btn(
                f"📖 {f['sura_name']} {format_ayah_number(f['ayah_number'])}",
                "qr_goto_ayah",
                {"aid": f["id"], "src": "favorites", "fp": page},
                color=_B,
                owner=owner
            )
        )

        if len(row) == 3:
            buttons.extend(reversed(row))  # عكس الصف
            row = []

    if row:
        buttons.extend(reversed(row))

    # --- أزرار التنقل ---
    nav = []

    if page < total_pages - 1:
        nav.append(btn("◀️", "qr_fav_page", {"p": page + 1}, color=_G, owner=owner))

    nav.append(btn("❌ إغلاق", "qr_close", {}, color=_R, owner=owner))

    if page > 0:
        nav.append(btn("▶️", "qr_fav_page", {"p": page - 1}, color=_G, owner=owner))

    buttons.extend(nav)

    # --- زر مسح المفضلة ---
    buttons.append(btn("🗑 مسح المفضلة", "qr_fav_clear_prompt", {"p": page},
                       color=_R, owner=owner))

    # --- layout ---
    fav_count = len(favs)

    rows = fav_count // 3
    remainder = fav_count % 3

    layout = [3] * rows
    if remainder:
        layout.append(remainder)

    if nav:
        layout.append(len(nav))

    layout.append(1)  # زر مسح المفضلة

    return buttons, layout

def build_sura_selection_text(page: int, total_pages: int) -> str:
    """نص اختيار السورة."""
    return f"📚 <b>اختر السورة</b> ({page+1}/{total_pages})\n\nاختر السورة لإضافة التفسير:"


def build_sura_buttons(suras: list[dict], uid: int, cid: int, page: int, total_pages: int) -> tuple[list, list]:
    """أزرار اختيار السورة مع ترقيم."""
    owner = (uid, cid)
    buttons = []

    # --- بناء أزرار السور مع عكس الصفوف ليظهر RTL ---
    row = []
    for sura in suras:
        row.append(
            btn(
                f"{sura['name']}",
                "qr_dev_tafseer_select_sura",
                {"sura_id": sura["id"]},
                color=_B,
                owner=owner
            )
        )

        if len(row) == 4:
            buttons.extend(reversed(row))  # عكس الصف ليظهر من اليمين
            row = []

    # لو بقي صف غير مكتمل
    if row:
        buttons.extend(reversed(row))

    # --- أزرار التنقل ---
    nav = []

    if page < total_pages - 1:
        nav.append(
            btn("التالي ◀️", "qr_dev_tafseer_sura_page", {"p": page + 1}, color=_G, owner=owner)
        )

    nav.append(
        btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)
    )


    if page > 0:
        nav.append(
            btn("▶️ السابق", "qr_dev_tafseer_sura_page", {"p": page - 1}, color=_G,owner=owner)
        )
    # إضافة أزرار التنقل بعد السور
    buttons.extend(nav)

    # --- layout ---
    sura_count = len(suras)

    rows = sura_count // 4
    remainder = sura_count % 4

    layout = [4] * rows
    if remainder:
        layout.append(remainder)

    # صف مستقل للتنقل
    if nav:
        layout.append(len(nav))

    return buttons, layout


def build_tafseer_type_buttons(uid: int, cid: int, sura: dict) -> tuple[list, list]:
    """أزرار اختيار نوع التفسير."""
    owner = (uid, cid)
    buttons = []

    for name_ar in db.TAFSEER_TYPES.keys():
        buttons.append(btn(
            name_ar,
            "qr_dev_tafseer_select_type",
            {"sura_id": sura["id"], "type": name_ar},
            color=_B, owner=owner
        ))

    buttons.append(btn("🔙 رجوع للسور", "qr_dev_tafseer_back_to_suras", {}, color=_R, owner=owner))
    layout = layout=[3,1]
    return buttons, layout


def build_ayah_input_text(sura: dict, tafseer_type: str) -> str:
    """نص إدخال رقم الآية."""
    return (
        f"📝 <b>إضافة تفسير {tafseer_type}</b>\n"
        f"<b>السورة:</b> {sura['name']}\n\n"
        f"أدخل رقم الآية التي يبدأ منها التفسير:"
    )


def build_bulk_tafseer_input_text(sura: dict, tafseer_type: str, start_ayah: int) -> str:
    """نص إدخال التفاسير المتعددة."""
    return (
        f"📚 <b>إضافة تفسير متعدد</b>\n"
        f"<b>السورة:</b> {sura['name']}\n"
        f"<b>نوع التفسير:</b> {tafseer_type}\n"
        f"<b>بدء من آية:</b> {start_ayah}\n\n"
        f"أرسل التفاسير مفصولة بـ:\n<code>{db.BULK_SEPARATOR}</code>\n\n"
        f"مثال:\nتفسير آية {start_ayah}\n{db.BULK_SEPARATOR}\nتفسير آية {start_ayah + 1}\n{db.BULK_SEPARATOR}\nتفسير آية {start_ayah + 2}"
    )


def build_single_tafseer_input_text(sura_name: str, ayah_number: int) -> str:
    """نص إدخال التفسير الفردي."""
    return (
        f"📖 <b>إضافة تفسير لسورة {sura_name} آية {ayah_number}</b>\n\n"
        f"أرسل التفاسير بالترتيب التالي:\n"
        f"<b>المختصر | الميسر | السعدي</b>\n\n"
        f"افصل بينهم باستخدام:\n<code>{db.BULK_SEPARATOR}</code>\n\n"
        f"مثال:\nتفسير المختصر هنا\n{db.BULK_SEPARATOR}\nتفسير الميسر هنا\n{db.BULK_SEPARATOR}\nتفسير السعدي هنا\n\n"
        f"<i>يمكنك ترك بعض التفاسير فارغة</i>"
    )

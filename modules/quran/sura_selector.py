"""
واجهة اختيار السورة المشتركة — قابلة لإعادة الاستخدام في:
  - إضافة آيات
  - إضافة تفسير
  - تصفح السور
تقبل callback_action لتحديد الإجراء عند اختيار السورة.
"""
from utils.pagination import btn, edit_ui, send_ui, paginate_list, register_action
from modules.quran import quran_db as db
from utils.helpers import get_lines

_B = "p"
_R = "d"
_G = "su"


def show_sura_selector(
    call_or_message,
    page: int,
    *,
    callback_action: str,
    cancel_action: str,
    page_action: str,
    title: str = "📚 اختر السورة",
    suras_source: str = "all",   # "all" | "with_ayat"
    edit: bool = True,
):
    """
    يعرض قائمة السور (4 في الصف) مع ترقيم.

    callback_action : الـ action الذي يُستدعى عند اختيار سورة (يستقبل sura_id)
    cancel_action   : الـ action عند الإلغاء
    page_action     : الـ action لتغيير الصفحة (يستقبل p, act, cact, pact)
    suras_source    : "all" لكل السور، "with_ayat" للسور التي بها آيات فقط
    """
    if hasattr(call_or_message, "from_user"):
        uid = call_or_message.from_user.id
        cid = call_or_message.message.chat.id if hasattr(call_or_message, "message") else call_or_message.chat.id
    else:
        uid = call_or_message.from_user.id
        cid = call_or_message.chat.id

    owner = (uid, cid)

    if suras_source == "with_ayat":
        suras = db.get_suras_with_ayat()
    else:
        suras = db.get_all_suras()

    if not suras:
        text = "❌ لا توجد سور في قاعدة البيانات."
        if edit:
            edit_ui(call_or_message, text=text, buttons=[], layout=[])
        else:
            send_ui(cid, text=text, buttons=[], layout=[], owner_id=uid)
        return

    items, total_pages = paginate_list(suras, page, per_page=60)
    text = f"{title} ({page+1}/{total_pages})\n{get_lines()}"

    buttons = []
    row = []
    for sura in items:
        row.append(btn(
            sura["name"],
            callback_action,
            {"sura_id": sura["id"]},
            color=_B, owner=owner,
        ))
        if len(row) == 4:
            buttons.extend(reversed(row))
            row = []
    if row:
        buttons.extend(reversed(row))

    # أزرار التنقل
    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", page_action,
                       {"p": page + 1, "act": callback_action,
                        "cact": cancel_action, "pact": page_action},
                       color=_G, owner=owner))
    nav.append(btn("❌ إلغاء", cancel_action, {}, color=_R, owner=owner))
    if page > 0:
        nav.append(btn("▶️ السابق", page_action,
                       {"p": page - 1, "act": callback_action,
                        "cact": cancel_action, "pact": page_action},
                       color=_G, owner=owner))
    buttons.extend(nav)

    sura_count = len(items)
    rows_full  = sura_count // 4
    remainder  = sura_count % 4
    layout     = [4] * rows_full
    if remainder:
        layout.append(remainder)
    if nav:
        layout.append(len(nav))

    if edit:
        edit_ui(call_or_message, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout, owner_id=uid)

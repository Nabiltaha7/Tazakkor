"""
handlers/group_admin/developer/dev_control_panel.py
─────────────────────────────────────────────────────
لوحة إدارة القرآن للمطور — بحث / تعديل / إضافة آيات / تفسير / إحصائيات
"""
from core.bot import bot
from core.admin import is_any_dev
from core.state_manager import StateManager
from utils.pagination import (
    btn, edit_ui, register_action,
    paginate_list, set_state, get_state, clear_state,
)
from utils.pagination.buttons import build_keyboard
from utils.helpers import get_lines, format_ayah_number
from modules.quran import quran_db as qr_db
from modules.quran import quran_service as qr_svc

_B = "p"
_G = "su"
_R = "d"
_PER_PAGE = 5


# ══════════════════════════════════════════
# QURAN DEV PANEL — entry point called from admin_panel
# ══════════════════════════════════════════

def _show_quran_dev_panel(call):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    text  = f"📖 <b>إدارة القرآن</b>\n{get_lines()}\n\nاختر العملية:"
    buttons = [
        btn("🔍 بحث آية",       "qr_dev_search",       {}, color=_B, owner=owner),
        btn("✏️ تعديل آية",     "qr_dev_edit_ayah",    {}, color=_B, owner=owner),
        btn("📖 تعديل تفسير",   "qr_dev_edit_tafseer", {}, color=_B, owner=owner),
        btn("➕ إضافة آيات",     "qr_dev_add_ayat",     {}, color=_B, owner=owner),
        btn("📊 إحصائيات",      "qr_dev_stats",        {}, color=_G, owner=owner),
        btn("🔙 رجوع",          "adm_main_back",       {}, color=_R, owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 1, 1])


# ══════════════════════════════════════════
# QURAN — SEARCH AYAH
# ══════════════════════════════════════════

@register_action("qr_dev_search")
def on_qr_dev_search(call, data):
    """بدء البحث عن آية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_search", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"🔍 <b>البحث في القرآن</b>\n\n"
            f"أرسل كلمة أو جزء من الآية أو رقم الآية:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — EDIT AYAH
# ══════════════════════════════════════════

@register_action("qr_dev_edit_ayah")
def on_qr_dev_edit_ayah(call, data):
    """بدء تعديل آية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_edit_ayah", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل آية</b>\n\n"
            f"أرسل:\n"
            f"اسم السورة + رقم الآية\n"
            f"أو رقم الآية مباشرة\n\n"
            f"مثال: البقرة 255\n"
            f"أو: 255",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — EDIT TAFSEER
# ══════════════════════════════════════════

@register_action("qr_dev_edit_tafseer")
def on_qr_dev_edit_tafseer(call, data):
    """بدء تعديل تفسير"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_edit_tafseer", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"📖 <b>تعديل تفسير</b>\n\n"
            f"أرسل رقم الآية:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — ADD AYAT
# ══════════════════════════════════════════

@register_action("qr_dev_add_ayat")
def on_qr_dev_add_ayat(call, data):
    """بدء إضافة آيات — يستخدم تدفق qr_dev_add"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    StateManager.set(uid, cid, {
        "type":  "qr_dev_add",
        "step":  "await_sura",
        "mid":   call.message.message_id,
        "extra": {},
    }, ttl=300)

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            "➕ <b>إضافة آيات</b>\n\nأرسل اسم السورة:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — STATISTICS
# ══════════════════════════════════════════

@register_action("qr_dev_stats")
def on_qr_dev_stats(call, data):
    from database.db_queries.quran_queries import get_total_ayat, get_next_tafseer_ayah
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)

    total_ayat = get_total_ayat()
    total_favs = len(qr_db.get_favorites(uid))

    # عد الآيات التي لها تفسير لكل نوع
    tafseer_counts = {}
    for name_ar, col in qr_db.TAFSEER_TYPES.items():
        from database.connection import get_db_conn
        cur = get_db_conn().cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM ayat WHERE {col} IS NOT NULL AND {col} != ''"
        )
        tafseer_counts[name_ar] = cur.fetchone()[0]

    text = (
        f"📊 <b>إحصائيات القرآن</b>\n{get_lines()}\n\n"
        f"📖 إجمالي الآيات: <b>{total_ayat:,}</b>\n\n"
        f"📚 التفاسير المُدخَلة:\n"
    )
    for name_ar, count in tafseer_counts.items():
        pct = round(count / total_ayat * 100) if total_ayat else 0
        text += f"• {name_ar}: <b>{count:,}</b> ({pct}%)\n"
    text += f"\n⭐️ مفضلتك: <b>{total_favs}</b> آية"

    edit_ui(call, text=text,
            buttons=[btn("🔙 رجوع", "adm_quran_panel", {}, color=_R, owner=owner)],
            layout=[1])


# qr_dev_cancel is registered in quran_handler.py — no duplicate here
# ══════════════════════════════════════════
# INPUT HANDLER — delegates to dev_flows.py
# ══════════════════════════════════════════

def handle_developer_input(message) -> bool:
    from handlers.group_admin.developer.dev_flows import dispatch
    return dispatch(message, message.from_user.id, message.chat.id)


@register_action("qr_dev_search_page")
def on_qr_dev_search_page(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    query = data.get("q", "")
    page  = int(data.get("p", 0))

    results = qr_svc.search(query)
    if not results:
        bot.answer_callback_query(call.id, "لا توجد نتائج.", show_alert=True)
        return

    # results may be (list, int) tuple from svc.search
    if isinstance(results, tuple):
        results = results[0]

    items, total_pages = paginate_list(results, page, per_page=_PER_PAGE)
    text = f"🔍 <b>نتائج البحث: {query}</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    for r in items:
        text += f"📖 <b>{r['sura_name']}</b> — آية {r['ayah_number']}\n{r['text_with_tashkeel']}\n\n"

    buttons = [
        btn(f"📖 {r['sura_name']} {r['ayah_number']}", "qr_dev_select_ayah",
            {"aid": r["id"]}, color=_B, owner=owner)
        for r in items
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "qr_dev_search_page", {"q": query, "p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "qr_dev_search_page", {"q": query, "p": page + 1}, owner=owner))
    nav.append(btn("❌ إغلاق", "qr_dev_cancel", {}, color=_R, owner=owner))
    buttons += nav
    layout = [1] * len(items) + ([len(nav)] if nav else [1])

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            text, cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard(buttons, layout, uid),
        )
    except Exception:
        pass


@register_action("qr_dev_select_ayah")
def on_qr_dev_select_ayah(call, data):
    """عرض آية محددة للمطور مع أزرار التحكم"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, " الآية غير موجودة.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        f"📖 <b>{ayah['sura_name']}</b>\n"
        f"{get_lines()}\n\n"
        f"{ayah['text_with_tashkeel']} {format_ayah_number(ayah['ayah_number'])}\n\n"
        f"{get_lines()}\n"
        f"<i>آية #{ayah['id']}</i>"
    )

    buttons = [
        btn("✏️ تعديل",       "qr_dev_edit_ayah_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("📖 تعديل تفسير", "qr_dev_edit_tafseer_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("⬅️ رجوع",        "qr_dev_search", {}, color=_R, owner=owner),
    ]

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1])


@register_action("qr_dev_edit_ayah_selected")
def on_qr_dev_edit_ayah_selected(call, data):
    """تعديل نص الآية المحددة"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, " الآية غير موجودة.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_edit_ayah_text", data={
        "aid": aid,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل آية #{aid}</b>\n"
            f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
            f"النص الحالي:\n<code>{ayah['text_with_tashkeel']}</code>\n\n"
            f"أرسل النص الجديد:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("qr_dev_edit_tafseer_selected")
def on_qr_dev_edit_tafseer_selected(call, data):
    """اختيار نوع التفسير للتعديل"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, " الآية غير موجودة.", show_alert=True)
        return

    _show_tafseer_selection(None, call.from_user.id, call.message.chat.id, ayah, call.message.message_id)


def _show_tafseer_selection(message, uid, cid, ayah, mid):
    """عرض أزرار اختيار التفسير"""
    text = (
        f"📖 <b>تعديل تفسير</b>\n"
        f"<b>{ayah['sura_name']}</b> {format_ayah_number(ayah['ayah_number'])}\n"
        f"{get_lines()}\n\n"
        f"اختر نوع التفسير:"
    )

    owner = (uid, cid)
    buttons = [
        btn(name_ar, "qr_dev_choose_tafseer", {"aid": ayah["id"], "col": col}, color=_B, owner=owner)
        for name_ar, col in qr_db.TAFSEER_TYPES.items()
    ]
    buttons.append(btn(" إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner))

    if mid:
        try:
            from utils.pagination.buttons import build_keyboard
            bot.edit_message_text(
                text, cid, mid,
                parse_mode="HTML",
                reply_markup=build_keyboard(buttons, layout=[3,1], owner_id=uid),
            )
        except Exception:
            pass


# qr_dev_choose_tafseer is registered in quran_handler.py

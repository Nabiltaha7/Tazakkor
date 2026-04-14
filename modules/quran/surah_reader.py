"""
قراءة سورة — نظام مستقل عن التلاوة.

التدفق:
  قراءة سورة → قائمة السور → اختر سورة
    → إذا يوجد تقدم: عرض خيار متابعة / من البداية
    → قراءة الآيات مع تتبع الختمة
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list
from utils.helpers import get_lines
from modules.quran import quran_db as db
from modules.quran import quran_service as svc

_B = "p"
_G = "su"
_R = "d"
_SURAS_PER_PAGE = 40


# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

def handle_surah_read_command(message) -> bool:
    if (message.text or "").strip() != "قراءة سورة":
        return False
    uid = message.from_user.id
    cid = message.chat.id
    _show_sura_list(cid, uid, page=0, reply_to=message.message_id)
    return True


# ══════════════════════════════════════════
# Surah list
# ══════════════════════════════════════════

def _show_sura_list(cid, uid, page, reply_to=None, call=None, back_action=None):
    suras = db.get_suras_with_ayat()
    if not suras:
        msg = "📚 لا توجد سور في قاعدة البيانات بعد."
        if call:
            edit_ui(call, text=msg, buttons=[], layout=[])
        else:
            bot.send_message(cid, msg)
        return

    items, total_pages = paginate_list(suras, page, per_page=_SURAS_PER_PAGE)
    owner = (uid, cid)

    text = (
        f"📚 <b>قراءة سورة</b>  ({page+1}/{total_pages})\n"
        f"{get_lines()}\n\n"
        "اختر السورة التي تريد قراءتها:"
    )

    buttons = []
    row_buf = []
    for s in items:
        row_buf.append(btn(s["name"], "sr_pick_sura",
                           {"sid": s["id"], "p": page}, owner=owner, color=_B))
        if len(row_buf) == 4:
            buttons.extend(reversed(row_buf))
            row_buf = []
    if row_buf:
        buttons.extend(reversed(row_buf))

    # back_action controls where the close/back button goes
    close_action = back_action or "sr_close"
    close_label  = "🔙 رجوع" if back_action else "❌ إغلاق"
    close_data   = {}

    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "sr_sura_page", {"p": page + 1, "ba": back_action or ""}, owner=owner, color=_G))
    nav.append(btn(close_label, close_action, close_data, owner=owner, color=_R))
    if page > 0:
        nav.append(btn("▶️ السابق", "sr_sura_page", {"p": page - 1, "ba": back_action or ""}, owner=owner, color=_G))
    buttons.extend(nav)

    count  = len(items)
    layout = [4] * (count // 4)
    if count % 4:
        layout.append(count % 4)
    layout.append(len(nav))

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("sr_sura_page")
def on_sura_page(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = int(data.get("p", 0))
    ba   = data.get("ba") or None
    bot.answer_callback_query(call.id)
    _show_sura_list(cid, uid, page, call=call, back_action=ba)


@register_action("sr_pick_sura")
def on_pick_sura(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    lp  = int(data.get("p", 0))
    bot.answer_callback_query(call.id)

    sura = db.get_sura(sid)
    if not sura:
        bot.answer_callback_query(call.id, "❌ السورة غير موجودة.", show_alert=True)
        return

    last_ayah_num = db.get_surah_read_progress(uid, sid)
    owner = (uid, cid)

    # If user has prior progress (not at ayah 1), offer resume or restart
    if last_ayah_num > 1:
        text = (
            f"📖 <b>لديك تقدم سابق في سورة {sura['name']}</b>\n\n"
            f"آخر آية قرأتها: <b>{last_ayah_num}</b>\n\n"
            "ماذا تريد؟"
        )
        buttons = [
            btn("▶️ متابعة",     "sr_resume",   {"sid": sid, "lp": lp, "an": last_ayah_num}, owner=owner, color=_G),
            btn("🔄 من البداية", "sr_restart",  {"sid": sid, "lp": lp},                      owner=owner, color=_B),
            btn("🔙 قائمة السور","sr_back_list", {"lp": lp},                                  owner=owner, color=_R),
        ]
        edit_ui(call, text=text, buttons=buttons, layout=[2, 1])
    else:
        # First time — go straight to ayah 1
        ayah = db.get_ayah_by_sura_number(sid, 1)
        if not ayah:
            bot.answer_callback_query(call.id, "❌ لا توجد آيات في هذه السورة.", show_alert=True)
            return
        _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_resume")
def on_resume(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    lp  = int(data.get("lp", 0))
    an  = int(data.get("an", 1))
    bot.answer_callback_query(call.id)

    ayah = db.get_ayah_by_sura_number(sid, an)
    if not ayah:
        ayah = db.get_ayat_by_sura(sid)[0] if db.get_ayat_by_sura(sid) else None
    if not ayah:
        bot.answer_callback_query(call.id, "❌ لا توجد آيات.", show_alert=True)
        return
    _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_restart")
def on_restart(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    lp  = int(data.get("lp", 0))
    bot.answer_callback_query(call.id)

    db.save_surah_read_progress(uid, sid, 1)
    ayah = db.get_ayah_by_sura_number(sid, 1)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ لا توجد آيات.", show_alert=True)
        return
    _show_ayah(uid, cid, ayah, sid, lp, call=call)


# ══════════════════════════════════════════
# Ayah display
# ══════════════════════════════════════════

def _show_ayah(uid, cid, ayah, sid, list_page, call=None, reply_to=None, returned=False):
    """Render ayah, save surah progress, and update khatmah."""
    db.save_surah_read_progress(uid, sid, ayah["ayah_number"])
    db.update_khatma(uid, sid, ayah["ayah_number"])   # khatmah tracking

    sura     = db.get_sura(sid)
    total    = sura.get("ayah_count") or len(db.get_ayat_by_sura(sid))
    is_fav   = db.is_favorite(uid, ayah["id"])
    has_prev = ayah["ayah_number"] > 1
    has_next = ayah["ayah_number"] < total

    owner = (uid, cid)
    aid   = ayah["id"]
    ctx   = {"aid": aid, "sid": sid, "lp": list_page}

    # Deep-link label when returning from khatmah
    returned_line = "\n📍 <i>عدت لآخر موضع قراءتك</i>" if returned else ""

    text = (
        f"📖 <b>{sura['name']}</b>  —  آية {ayah['ayah_number']} / {total}\n"
        f"‏━━━━━━━━━━━━━━━\n\n"
        f"{ayah['text_with_tashkeel']}\n\n"
        f"‏━━━━━━━━━━"
        + returned_line
    )

    nav = []
    if has_next:
        nav.append(btn("⬅️ التالية",  "sr_next", ctx, color=_B, owner=owner))
    if has_prev:
        nav.append(btn("➡️ السابقة", "sr_prev", ctx, color=_B, owner=owner))

    fav_label = "💛 إزالة" if is_fav else "⭐️ مفضلة"
    action_row = [
        btn("📖 تفسير",      "sr_tafseer",  {"aid": aid, "sid": sid, "lp": list_page}, color=_B, owner=owner),
        btn(fav_label,       "sr_fav",      ctx,                                        color=_G, owner=owner),
        btn("🔙 قائمة السور","sr_back_list",{"lp": list_page},                          color=_R, owner=owner),
    ]

    buttons = nav + action_row
    layout  = ([len(nav)] if nav else []) + [3]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("sr_next")
def on_next(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    aid = data["aid"]
    lp  = int(data.get("lp", 0))
    bot.answer_callback_query(call.id)

    ayah = db.get_next_ayah(aid)
    if not ayah or ayah["sura_id"] != sid:
        bot.answer_callback_query(call.id, "✅ وصلت لآخر آية في السورة!", show_alert=True)
        return
    _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_prev")
def on_prev(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    aid = data["aid"]
    lp  = int(data.get("lp", 0))
    bot.answer_callback_query(call.id)

    ayah = db.get_prev_ayah(aid)
    if not ayah or ayah["sura_id"] != sid:
        bot.answer_callback_query(call.id, "⬅️ هذه أول آية في السورة.", show_alert=True)
        return
    _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_fav")
def on_fav(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    sid = int(data["sid"])
    aid = data["aid"]
    lp  = int(data.get("lp", 0))
    _, msg = svc.toggle_favorite(uid, aid)
    bot.answer_callback_query(call.id, msg)
    ayah = db.get_ayah(aid)
    if ayah:
        _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_tafseer")
def on_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    sid  = int(data["sid"])
    lp   = int(data.get("lp", 0))
    ayah = db.get_ayah(aid)

    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    available = svc.get_available_tafseer(ayah)
    if not available:
        bot.answer_callback_query(call.id, "لم يتم إضافة تفسير بعد.", show_alert=True)
        return

    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    tafseer_btns = [
        btn(name_ar, "sr_show_tafseer",
            {"aid": aid, "col": col, "sid": sid, "lp": lp},
            color=_B, owner=owner)
        for name_ar, col in available
    ]
    tafseer_btns.append(btn("🔙 رجوع", "sr_back_ayah",
                            {"aid": aid, "sid": sid, "lp": lp}, color=_R, owner=owner))
    n = len(available)
    layout = ([3] if n >= 3 else [n]) + [1]
    edit_ui(call,
            text=(
                f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n{ayah['text_with_tashkeel']}\n\n"
                f"{get_lines()}\nاختر التفسير:"
            ),
            buttons=tafseer_btns, layout=layout)


@register_action("sr_show_tafseer")
def on_show_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    col  = data["col"]
    sid  = int(data["sid"])
    lp   = int(data.get("lp", 0))
    ayah = db.get_ayah(aid)

    if not ayah or not col:
        bot.answer_callback_query(call.id, "❌ خطأ.", show_alert=True)
        return
    content = ayah.get(col) or ""
    if not content:
        bot.answer_callback_query(call.id, "لم يتم إضافة هذا التفسير بعد.", show_alert=True)
        return

    name_ar = next((k for k, v in db.TAFSEER_TYPES.items() if v == col), col)
    owner   = (uid, cid)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"📖 <b>تفسير {name_ar}</b>\n"
                f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n{ayah['text_with_tashkeel']}\n\n"
                f"{get_lines()}\n📝 <b>التفسير:</b>\n{content}"
            ),
            buttons=[btn("🔙 رجوع للتفاسير", "sr_tafseer",
                         {"aid": aid, "sid": sid, "lp": lp}, color=_R, owner=owner)],
            layout=[1])


@register_action("sr_back_ayah")
def on_back_ayah(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    sid  = int(data["sid"])
    lp   = int(data.get("lp", 0))
    ayah = db.get_ayah(aid)
    bot.answer_callback_query(call.id)
    if ayah:
        _show_ayah(uid, cid, ayah, sid, lp, call=call)


@register_action("sr_back_list")
def on_back_list(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    lp  = int(data.get("lp", 0))
    bot.answer_callback_query(call.id)
    _show_sura_list(cid, uid, page=lp, call=call)


@register_action("sr_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# ختمتي — قراءة متواصلة عبر القرآن كاملاً
# ══════════════════════════════════════════

def _show_khatmah_ayah(uid, cid, ayah, call=None, reply_to=None, returned=False):
    """
    عرض آية في وضع الختمة المتواصلة.
    - التنقل يعبر حدود السور تلقائياً (get_next/prev_ayah بدون قيد sura_id)
    - يحفظ موضع الختمة عند كل آية
    """
    db.save_surah_read_progress(uid, ayah["sura_id"], ayah["ayah_number"])
    db.update_khatma(uid, ayah["sura_id"], ayah["ayah_number"])

    sura      = db.get_sura(ayah["sura_id"])
    sura_name = sura["name"] if sura else f"سورة {ayah['sura_id']}"
    sura_total = sura.get("ayah_count") or len(db.get_ayat_by_sura(ayah["sura_id"]))

    is_fav   = db.is_favorite(uid, ayah["id"])
    has_prev = db.get_prev_ayah(ayah["id"]) is not None
    has_next = db.get_next_ayah(ayah["id"]) is not None

    owner = (uid, cid)
    aid   = ayah["id"]

    returned_line = "\n📍 <i>عدت لآخر موضع قراءتك</i>" if returned else ""

    text = (
        f"🕌 <b>ختمتي</b> — <b>{sura_name}</b>  آية {ayah['ayah_number']} / {sura_total}\n"
        f"‏━━━━━━━━━━━━━━━\n\n"
        f"{ayah['text_with_tashkeel']}\n\n"
        f"‏━━━━━━━━━━"
        + returned_line
    )

    nav = []
    if has_next:
        nav.append(btn("⬅️ التالية", "kh_next", {"aid": aid}, color=_B, owner=owner))
    if has_prev:
        nav.append(btn("➡️ السابقة", "kh_prev", {"aid": aid}, color=_B, owner=owner))

    fav_label = "💛 إزالة" if is_fav else "⭐️ مفضلة"
    action_row = [
        btn("📖 تفسير",    "kh_tafseer",  {"aid": aid}, color=_B, owner=owner),
        btn(fav_label,     "kh_fav",      {"aid": aid}, color=_G, owner=owner),
        btn("🔙 ختمتي",   "kh_back_main", {},           color=_R, owner=owner),
    ]

    buttons = nav + action_row
    layout  = ([len(nav)] if nav else []) + [3]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("kh_next")
def on_kh_next(call, data):
    """التالية في وضع الختمة — يعبر السور تلقائياً."""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    bot.answer_callback_query(call.id)

    ayah = db.get_next_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "🎉 أكملت القرآن الكريم!", show_alert=True)
        return
    _show_khatmah_ayah(uid, cid, ayah, call=call)


@register_action("kh_prev")
def on_kh_prev(call, data):
    """السابقة في وضع الختمة — يعبر السور تلقائياً."""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    bot.answer_callback_query(call.id)

    ayah = db.get_prev_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "⬅️ هذه أول آية في القرآن.", show_alert=True)
        return
    _show_khatmah_ayah(uid, cid, ayah, call=call)


@register_action("kh_fav")
def on_kh_fav(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    _, msg = svc.toggle_favorite(uid, aid)
    bot.answer_callback_query(call.id, msg)
    ayah = db.get_ayah(aid)
    if ayah:
        _show_khatmah_ayah(uid, cid, ayah, call=call)


@register_action("kh_tafseer")
def on_kh_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    ayah = db.get_ayah(aid)

    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    available = svc.get_available_tafseer(ayah)
    if not available:
        bot.answer_callback_query(call.id, "لم يتم إضافة تفسير بعد.", show_alert=True)
        return

    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    tafseer_btns = [
        btn(name_ar, "kh_show_tafseer",
            {"aid": aid, "col": col},
            color=_B, owner=owner)
        for name_ar, col in available
    ]
    tafseer_btns.append(btn("🔙 رجوع", "kh_back_ayah", {"aid": aid}, color=_R, owner=owner))
    n = len(available)
    layout = ([3] if n >= 3 else [n]) + [1]
    edit_ui(call,
            text=(
                f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n{ayah['text_with_tashkeel']}\n\n"
                f"{get_lines()}\nاختر التفسير:"
            ),
            buttons=tafseer_btns, layout=layout)


@register_action("kh_show_tafseer")
def on_kh_show_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    col  = data["col"]
    ayah = db.get_ayah(aid)

    if not ayah or not col:
        bot.answer_callback_query(call.id, "❌ خطأ.", show_alert=True)
        return
    content = ayah.get(col) or ""
    if not content:
        bot.answer_callback_query(call.id, "لم يتم إضافة هذا التفسير بعد.", show_alert=True)
        return

    name_ar = next((k for k, v in db.TAFSEER_TYPES.items() if v == col), col)
    owner   = (uid, cid)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"📖 <b>تفسير {name_ar}</b>\n"
                f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n{ayah['text_with_tashkeel']}\n\n"
                f"{get_lines()}\n📝 <b>التفسير:</b>\n{content}"
            ),
            buttons=[btn("🔙 رجوع للتفاسير", "kh_tafseer",
                         {"aid": aid}, color=_R, owner=owner)],
            layout=[1])


@register_action("kh_back_ayah")
def on_kh_back_ayah(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data["aid"]
    ayah = db.get_ayah(aid)
    bot.answer_callback_query(call.id)
    if ayah:
        _show_khatmah_ayah(uid, cid, ayah, call=call)

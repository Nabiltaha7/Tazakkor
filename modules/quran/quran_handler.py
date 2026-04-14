"""
معالج نظام إنجاز القرآن — التفاعل مع البوت فقط
"""
from core.bot import bot
from core.admin import is_any_dev
from utils.pagination import (
    btn, send_ui, edit_ui, register_action,
    paginate_list, set_state, get_state, clear_state,
)
from utils.pagination.buttons import build_keyboard

from modules.quran import quran_db as db
from modules.quran import quran_service as svc
from modules.quran import quran_ui as ui
from utils.helpers import get_lines

# ── تهيئة الجداول عند الاستيراد ──
db.create_tables()

_B = "p"
_G = "su"
_R = "d"
_PER_PAGE = 5


# ══════════════════════════════════════════
# 📖 التلاوة
# ══════════════════════════════════════════

def handle_tilawa(message) -> bool:
    """أمر: تلاوة"""
    if (message.text or "").strip() != "تلاوة":
        return False

    uid = message.from_user.id
    cid = message.chat.id

    ayah = svc.get_current_ayah(uid)
    if not ayah:
        bot.reply_to(message,
                     "📖 لا توجد آيات في قاعدة البيانات بعد.\n"
                     "يمكن للمطور إضافة آيات باستخدام أمر الإضافة.")
        return True

    _send_ayah(message, uid, cid, ayah, reply_to=message.message_id)
    return True


def _send_ayah(message_or_none, uid: int, cid: int, ayah: dict,
               reply_to: int = None, edit_call=None,
               source: str = None, fav_page: int = 0):
    """يرسل أو يعدّل رسالة الآية."""
    total    = db.get_total_ayat()
    is_fav   = db.is_favorite(uid, ayah["id"])
    has_prev = db.get_prev_ayah(ayah["id"]) is not None
    has_next = db.get_next_ayah(ayah["id"]) is not None

    text, (buttons, layout) = (
        ui.build_ayah_text(ayah, total),
        ui.build_ayah_buttons(uid, cid, ayah, is_fav, has_prev, has_next,
                              source=source, fav_page=fav_page),
    )

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
        if source not in ("favorites", "search"):
            svc.save_position(uid, ayah["id"], edit_call.message.message_id)
            db.update_khatma(uid, ayah["sura_id"], ayah["ayah_number"])
    else:
        sent = send_ui(cid, text=text, buttons=buttons, layout=layout,
                       owner_id=uid, reply_to=reply_to)
        if sent and source not in ("favorites", "search"):
            svc.save_position(uid, ayah["id"], sent.message_id)
            db.update_khatma(uid, ayah["sura_id"], ayah["ayah_number"])


# ── التنقل ──

@register_action("qr_next")
def on_next(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    ayah = db.get_next_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "✅ وصلت لآخر آية!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(None, uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0))


@register_action("qr_prev")
def on_prev(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    ayah = db.get_prev_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "⬅️ هذه أول آية.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(None, uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0))


@register_action("qr_goto_ayah")
def on_goto(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    ayah = db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(None, uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0))


@register_action("qr_back_to_ayah")
def on_back_to_ayah(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    ayah = db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(None, uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0))


@register_action("qr_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# ⭐️ المفضلة
# ══════════════════════════════════════════

@register_action("qr_fav")
def on_fav(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    aid = data.get("aid")

    is_now_fav, msg = svc.toggle_favorite(uid, aid)
    bot.answer_callback_query(call.id, msg, show_alert=False)

    ayah = db.get_ayah(aid)
    if ayah:
        _send_ayah(None, uid, cid, ayah, edit_call=call,
                   source=data.get("src"), fav_page=data.get("fp", 0))


def handle_my_favorites(message) -> bool:
    """أمر: مفضلتي"""
    if (message.text or "").strip() != "مفضلتي":
        return False

    uid  = message.from_user.id
    cid  = message.chat.id
    favs = svc.get_user_favorites(uid)

    if not favs:
        bot.reply_to(message, "⭐️ مفضلتك فارغة.\nاضغط ⭐️ على أي آية لإضافتها.")
        return True

    _show_favorites(message, uid, cid, favs, page=0, reply_to=message.message_id)
    return True


def _show_favorites(message_or_none, uid: int, cid: int,
                    favs: list, page: int, reply_to: int = None, edit_call=None):
    items, total_pages = paginate_list(favs, page, per_page=_PER_PAGE)
    text    = ui.build_favorites_text(items, page, total_pages)
    buttons, layout = ui.build_favorites_buttons(uid, cid, items, page, total_pages)

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("qr_fav_page")
def on_fav_page(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = int(data.get("p", 0))
    favs = svc.get_user_favorites(uid)
    bot.answer_callback_query(call.id)
    _show_favorites(None, uid, cid, favs, page, edit_call=call)


@register_action("qr_back_favorites")
def on_back_favorites(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = int(data.get("fp", 0))
    favs = svc.get_user_favorites(uid)
    bot.answer_callback_query(call.id)
    if not favs:
        bot.answer_callback_query(call.id, "⭐️ مفضلتك فارغة.", show_alert=True)
        return
    _show_favorites(None, uid, cid, favs, page, edit_call=call)


@register_action("qr_fav_clear_prompt")
def on_fav_clear_prompt(call, data):
    """يعرض أزرار تأكيد مسح المفضلة"""
    uid   = call.from_user.id
    cid   = call.message.chat.id
    page  = int(data.get("p", 0))
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text="🗑 <b>مسح المفضلة</b>\n\nهل أنت متأكد أنك تريد حذف جميع الآيات المحفوظة؟\n⚠️ لا يمكن التراجع عن هذا الإجراء.",
            buttons=[
                btn("✅ تأكيد المسح", "qr_fav_clear_confirm", {"p": page},
                    color="d", owner=owner),
                btn("❌ إلغاء", "qr_fav_clear_cancel", {"p": page},
                    color="su", owner=owner),
            ],
            layout=[2])


@register_action("qr_fav_clear_confirm")
def on_fav_clear_confirm(call, data):
    """يحذف جميع مفضلات المستخدم"""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = int(data.get("p", 0))
    deleted = db.clear_favorites(uid)
    bot.answer_callback_query(call.id,
                              f"✅ تم مسح {deleted} آية من مفضلتك." if deleted
                              else "⭐️ مفضلتك كانت فارغة.",
                              show_alert=True)
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


@register_action("qr_fav_clear_cancel")
def on_fav_clear_cancel(call, data):
    """يرجع لقائمة المفضلة بدون حذف"""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = int(data.get("p", 0))
    favs = svc.get_user_favorites(uid)
    bot.answer_callback_query(call.id)
    if not favs:
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        return
    _show_favorites(None, uid, cid, favs, page, edit_call=call)


# ══════════════════════════════════════════
# 📖 التفسير
# ══════════════════════════════════════════

@register_action("qr_tafseer")
def on_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    ayah = db.get_ayah(aid)

    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    available = svc.get_available_tafseer(ayah)
    if not available:
        bot.answer_callback_query(
            call.id,
            "لم يتم إضافة تفسير بعد لهذه الآية",
            show_alert=True,
        )
        return

    sura      = db.get_sura(ayah["sura_id"])
    sura_name = sura["name"] if sura else f"سورة {ayah['sura_id']}"
    source    = data.get("src")
    fav_page  = data.get("fp", 0)

    buttons, layout = ui.build_tafseer_buttons(uid, cid, ayah,
                                               source=source, fav_page=fav_page)
    bot.answer_callback_query(call.id)
    edit_ui(
        call,
        text=(
            f"📖 <b>{sura_name}</b> — آية {ayah['ayah_number']}\n"
            f"{get_lines()}\n\n"
            f"{ayah['text_with_tashkeel']}\n\n"
            f"{get_lines()}\n"
            f"اختر التفسير:"
        ),
        buttons=buttons,
        layout=layout,
    )


@register_action("qr_show_tafseer")
def on_show_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    col  = data.get("col")
    ayah = db.get_ayah(aid)

    if not ayah or not col:
        bot.answer_callback_query(call.id, "❌ خطأ.", show_alert=True)
        return

    content = ayah.get(col) or ""
    if not content:
        bot.answer_callback_query(call.id, "لم يتم إضافة هذا التفسير بعد.", show_alert=True)
        return

    name_ar   = next((k for k, v in db.TAFSEER_TYPES.items() if v == col), col)
    sura      = db.get_sura(ayah["sura_id"])
    sura_name = sura["name"] if sura else f"سورة {ayah['sura_id']}"
    source    = data.get("src")
    fav_page  = data.get("fp", 0)
    owner     = (uid, cid)

    back_ctx = {"aid": aid}
    if source:
        back_ctx["src"] = source
        back_ctx["fp"]  = fav_page

    bot.answer_callback_query(call.id)
    edit_ui(
        call,
        text=(
            f"📖 <b>تفسير {name_ar}</b>\n"
            f"<b>{sura_name}</b> — آية {ayah['ayah_number']}\n"
            f"{get_lines()}\n\n"
            f"{ayah['text_with_tashkeel']}\n\n"
            f"{get_lines()}\n"
            f"📝 <b>التفسير:</b>\n{content}"
        ),
        buttons=[btn("🔙 رجوع للتفاسير", "qr_tafseer", back_ctx, color=_R, owner=owner)],
        layout=[1],
    )


# ══════════════════════════════════════════
# 🔍 البحث
# ══════════════════════════════════════════

def handle_search(message) -> bool:
    """أمر: آية <نص البحث>"""
    text = (message.text or "").strip()
    if not text.startswith("آية "):
        return False

    query = text[4:]
    if not query:
        bot.reply_to(message, "❌ أدخل كلمة للبحث.\nمثال: <code>آية الرحمن</code>",
                     parse_mode="HTML")
        return True

    uid             = message.from_user.id
    cid             = message.chat.id
    results, total  = svc.search(query)

    if not results:
        bot.reply_to(
            message,
            f"🔍 لم يتم العثور على نتائج لـ: <b>{query}</b>",
            parse_mode="HTML",
        )
        return True

    _show_search_results(message, uid, cid, query, results, total, page=0,
                         reply_to=message.message_id)
    return True


def _show_search_results(message_or_none, uid: int, cid: int,
                          query: str, results: list, total_occurrences: int,
                          page: int, reply_to: int = None, edit_call=None):
    items, total_pages = paginate_list(results, page, per_page=_PER_PAGE)
    text    = ui.build_search_result_text(items, page, total_pages,
                                          query=query,
                                          ayat_count=len(results),
                                          total_occurrences=total_occurrences)
    buttons, layout = ui.build_search_buttons(uid, cid, query, page, total_pages, items)

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("qr_search_page")
def on_search_page(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    query = data.get("q", "")
    page  = int(data.get("p", 0))

    results, total = svc.search(query)
    bot.answer_callback_query(call.id)
    _show_search_results(None, uid, cid, query, results, total, page, edit_call=call)


# ══════════════════════════════════════════
# 🔁 مسح التقدم
# ══════════════════════════════════════════

def handle_reset(message) -> bool:
    """أمر: مسح تلاوتي"""
    if (message.text or "").strip() != "مسح تلاوتي":
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    send_ui(
        cid,
        text=(
            "🔁 <b>مسح تقدم التلاوة</b>\n\n"
            "هل تريد إعادة ضبط تقدمك والبدء من أول آية؟\n"
            "⚠️ لا يمكن التراجع عن هذا الإجراء."
        ),
        buttons=[
            btn("✅ نعم، امسح تقدمي", "qr_confirm_reset", {}, color=_R, owner=owner),
            btn("❌ إلغاء",            "qr_close",         {}, color=_B, owner=owner),
        ],
        layout=[2],
        owner_id=uid,
        reply_to=message.message_id,
    )
    return True


@register_action("qr_confirm_reset")
def on_confirm_reset(call, data):
    uid = call.from_user.id
    svc.reset_user(uid)
    bot.answer_callback_query(call.id, "✅ تم مسح تقدمك.", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 🛠 إدارة المحتوى (للمطورين)
# ══════════════════════════════════════════

def handle_dev_quran_input(message) -> bool:
    """
    يعالج حالات الانتظار الخاصة بإدارة القرآن.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    uid = message.from_user.id
    cid = message.chat.id

    if not is_any_dev(uid):
        return False

    state = get_state(uid, cid)
    if not state or "state" not in state:
        return False

    s     = state["state"]
    sdata = state.get("data", {})

    if not s.startswith("qr_dev_"):
        return False

    raw  = (message.text or "").strip()
    mid  = sdata.get("_mid")

    # ── تحديد ما إذا كانت هذه الحالة مدعومة هنا ──
    handled_states = {
        "qr_dev_add_ayat",
        "qr_dev_edit_ayah",
        "qr_dev_edit_tafseer",
        "qr_dev_edit_tafseer_text",
        "qr_dev_tafseer_single_sura_ayah",
        "qr_dev_tafseer_single_content",
        "qr_dev_tafseer_bulk_content",
    }
    if s not in handled_states:
        return False

    # ── الآن فقط: مسح الحالة + حذف رسالة المستخدم ──
    from utils.logger import log_event
    log_event("quran_input_handler", state=s)
    clear_state(uid, cid)

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    def _reply(text: str):
        if mid:
            try:
                bot.edit_message_text(text, cid, mid, parse_mode="HTML")
            except Exception:
                bot.send_message(cid, text, parse_mode="HTML")
        else:
            bot.send_message(cid, text, parse_mode="HTML")

    # ── إضافة آيات ──
    if s == "qr_dev_add_ayat":
        sura_name    = sdata.get("sura")
        start_number = int(sdata.get("start", 1))
        if not raw:
            _reply("❌ النص لا يمكن أن يكون فارغاً.")
            return True
        added = svc.bulk_add_ayat(sura_name, start_number, raw)
        _reply(
            f"✅ تمت إضافة <b>{added}</b> آية إلى سورة <b>{sura_name}</b>.\n"
            f"الفاصل المستخدم: <code>{db.BULK_SEPARATOR}</code>"
        )
        return True

    # ── تعديل نص آية ──
    if s == "qr_dev_edit_ayah":
        ayah_id = sdata.get("aid")
        if not raw:
            _reply("❌ النص لا يمكن أن يكون فارغاً.")
            return True
        ok = svc.edit_ayah(ayah_id, raw)
        _reply("✅ تم تعديل نص الآية." if ok else "❌ لم يتم العثور على الآية.")
        return True

    # ── تعديل تفسير ──
    if s in ("qr_dev_edit_tafseer", "qr_dev_edit_tafseer_text"):
        ayah_id    = sdata.get("aid")
        tafseer_col = sdata.get("col")
        if not raw:
            _reply("❌ النص لا يمكن أن يكون فارغاً.")
            return True
        ok = svc.edit_tafseer(ayah_id, tafseer_col, raw)
        _reply("✅ تم تعديل التفسير." if ok else "❌ فشل التعديل.")
        return True

    # ── إضافة تفسير آية واحدة ──
    if s == "qr_dev_tafseer_single_sura_ayah":
        try:
            sura_name, ayah_num = svc.parse_sura_ayah_input(raw)
            valid, error_msg, ayah = svc.validate_sura_ayah(sura_name, ayah_num)
            if not valid:
                _reply(error_msg)
                return True

            set_state(uid, cid, "qr_dev_tafseer_single_content",
                      {"sura": sura_name, "ayah": ayah_num, "_mid": mid})
            text = ui.build_single_tafseer_input_text(sura_name, ayah_num)
            _reply(text)
            return True
        except ValueError as e:
            _reply(f"❌ {str(e)}")
            return True

    # ── محتوى تفسير آية واحدة ──
    if s == "qr_dev_tafseer_single_content":
        sura_name = sdata.get("sura")
        ayah_num = sdata.get("ayah")
        if not sura_name or not ayah_num:
            _reply("❌ خطأ في البيانات.")
            return True

        parts = [p.strip() for p in raw.split(db.BULK_SEPARATOR) if p.strip()]
        if not parts:
            _reply("❌ يجب إدخال تفسير واحد على الأقل.")
            return True

        success, msg = svc.add_single_tafseer(sura_name, ayah_num, parts)
        _reply(msg)
        return True

    # ── محتوى التفسير المتعدد ──
    if s == "qr_dev_tafseer_bulk_content":
        sura_id = sdata.get("sura_id")
        tafseer_type = sdata.get("type")
        start_ayah = sdata.get("start")
        sura = db.get_sura(sura_id)

        if not sura or not tafseer_type or not start_ayah:
            _reply("❌ خطأ في البيانات.")
            return True

        parts = [p.strip() for p in raw.split(db.BULK_SEPARATOR) if p.strip()]
        if not parts:
            _reply("❌ يجب إدخال تفسير واحد على الأقل.")
            return True

        success, msg = svc.add_bulk_tafseer(sura["name"], tafseer_type, start_ayah, parts)
        _reply(msg)
        return True

    return False


def handle_dev_quran_command(message) -> bool:
    """
    أوامر إدارة القرآن للمطورين:
    - اضف آيات [سورة] [رقم_بداية]
    - عدل آية [id]
    - عدل تفسير [id]
    """
    if not is_any_dev(message.from_user.id):
        return False

    text  = (message.text or "").strip()
    parts = text.split()
    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    # ── اضف آيات [سورة] [رقم_بداية] ──
    if text.startswith("اضف آيات "):
        rest = text[9:].strip().split()
        if len(rest) < 1:
            bot.reply_to(message,
                         "❌ الصيغة: <code>اضف آيات </code> [اسم السورة] [رقم البداية]",
                         parse_mode="HTML")
            return True
        start_num = 1
        if len(rest) >= 2 and rest[-1].isdigit():
            start_num = int(rest[-1])
            sura_name = " ".join(rest[:-1])
        else:
            sura_name = " ".join(rest)

        set_state(uid, cid, "qr_dev_add_ayat",
                  data={"sura": sura_name, "start": start_num, "_mid": None})
        cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)
        bot.reply_to(
            message,
            f"✍️ <b>إضافة آيات — سورة {sura_name}</b>\n\n"
            f"أرسل الآيات. لإضافة عدة آيات دفعة واحدة، افصل بينها بـ:\n"
            f"<code>{db.BULK_SEPARATOR}</code>\n\n"
            f"مثال:\nبِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ\n---\nالْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
        return True

    # ── عدل آية [id] ──
    if text.startswith("عدل آية ") and len(parts) >= 3 and parts[2].isdigit():
        ayah_id = int(parts[2])
        ayah    = db.get_ayah(ayah_id)
        if not ayah:
            bot.reply_to(message, f"❌ لا توجد آية بالرقم {ayah_id}.")
            return True

        set_state(uid, cid, "qr_dev_edit_ayah",
                  data={"aid": ayah_id, "_mid": None})
        cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)
        bot.reply_to(
            message,
            f"✏️ <b>تعديل آية #{ayah_id}</b>\n"
            f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
            f"النص الحالي:\n<code>{ayah['text_with_tashkeel']}</code>\n\n"
            f"أرسل النص الجديد أو اضغط إلغاء:",
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
        return True

    # ── عدل تفسير [id] ──
    if text.startswith("عدل تفسير ") and len(parts) >= 3 and parts[2].isdigit():
        ayah_id = int(parts[2])
        ayah    = db.get_ayah(ayah_id)
        if not ayah:
            bot.reply_to(message, f"❌ لا توجد آية بالرقم {ayah_id}.")
            return True

        # اختيار نوع التفسير
        tafseer_buttons = [
            btn(name_ar, "qr_dev_choose_tafseer",
                {"aid": ayah_id, "col": col}, color=_B, owner=owner)
            for name_ar, col in db.TAFSEER_TYPES.items()
        ]
        tafseer_buttons.append(btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner))
        send_ui(
            cid,
            text=(
                f"✏️ <b>تعديل تفسير آية #{ayah_id}</b>\n"
                f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
                f"اختر نوع التفسير:"
            ),
            buttons=tafseer_buttons,
            layout=[3] + [1],
            owner_id=uid,
            reply_to=message.message_id,
        )
        return True

    return False


@register_action("qr_dev_choose_tafseer")
def on_dev_choose_tafseer(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    ayah_id = data.get("aid")
    col     = data.get("col")
    ayah    = db.get_ayah(ayah_id)
    owner   = (uid, cid)

    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    name_ar = next((k for k, v in db.TAFSEER_TYPES.items() if v == col), col)
    current = ayah.get(col) or "(لا يوجد تفسير)"

    set_state(uid, cid, "qr_dev_edit_tafseer",
              data={"aid": ayah_id, "col": col, "_mid": call.message.message_id,
                    "_step": "await_text"})
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل تفسير {name_ar}</b>\n"
            f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
            f"التفسير الحالي:\n<i>{current[:200]}</i>\n\n"
            f"أرسل التفسير الجديد أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("qr_dev_cancel")
def on_dev_cancel(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 🆕 نظام التفسير الجديد
# ══════════════════════════════════════════

def handle_add_ayat(message) -> bool:
    """أمر: إضافة آيات — يعرض واجهة اختيار السورة بدون إدخال يدوي"""
    if (message.text or "").strip() != "إضافة آيات":
        return False

    if not is_any_dev(message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return True

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    from modules.quran.sura_selector import show_sura_selector
    # نرسل رسالة جديدة ثم نعدّلها بواجهة السور
    sent = send_ui(
        cid,
        text="📖 <b>إضافة آيات</b>\n\nاختر السورة:",
        buttons=[btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)],
        layout=[1],
        owner_id=uid,
        reply_to=message.message_id,
    )
    if sent:
        # نعدّل الرسالة لتعرض واجهة السور
        import types as _types
        fake_call = _types.SimpleNamespace(
            from_user=message.from_user,
            message=sent,
        )
        show_sura_selector(
            fake_call, 0,
            callback_action="qr_dev_add_ayat_sura",
            cancel_action="qr_dev_cancel",
            page_action="qr_dev_add_ayat_page",
            title="📖 إضافة آيات — اختر السورة",
            suras_source="all",
            edit=True,
        )
    return True


@register_action("qr_dev_add_ayat_page")
def on_add_ayat_page(call, data):
    uid = call.from_user.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return
    from modules.quran.sura_selector import show_sura_selector
    page = int(data.get("p", 0))
    bot.answer_callback_query(call.id)
    show_sura_selector(
        call, page,
        callback_action="qr_dev_add_ayat_sura",
        cancel_action="qr_dev_cancel",
        page_action="qr_dev_add_ayat_page",
        title="📖 إضافة آيات — اختر السورة",
        suras_source="all",
        edit=True,
    )


@register_action("qr_dev_add_ayat_sura")
def on_add_ayat_sura(call, data):
    uid     = call.from_user.id
    cid     = call.message.chat.id
    owner   = (uid, cid)
    sura_id = data.get("sura_id")

    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    sura = db.get_sura(sura_id)
    if not sura:
        bot.answer_callback_query(call.id, "❌ السورة غير موجودة.", show_alert=True)
        return

    # تحديد رقم الآية التالية تلقائياً
    next_num = db.get_next_ayah_number(sura_id)
    bot.answer_callback_query(call.id)

    set_state(uid, cid, "qr_dev_add_ayat",
              data={"sura": sura["name"], "start": next_num, "_mid": call.message.message_id})

    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"📖 <b>إضافة آيات — سورة {sura['name']}</b>\n\n"
            f"▶️ ستبدأ الإضافة من الآية رقم: <b>{next_num}</b>\n\n"
            f"أرسل الآيات مفصولة بـ:\n<code>{db.BULK_SEPARATOR}</code>\n\n"
            f"مثال:\nبِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ\n{db.BULK_SEPARATOR}\nالْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("qr_dev_tafseer_bulk")
def on_tafseer_bulk(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    from modules.quran.sura_selector import show_sura_selector
    show_sura_selector(
        call, 0,
        callback_action="qr_dev_tafseer_select_sura",
        cancel_action="qr_dev_cancel",
        page_action="qr_dev_tafseer_sura_page",
        title="📝 إضافة تفسير — اختر السورة",
        suras_source="with_ayat",
        edit=True,
    )


def handle_add_tafseer(message) -> bool:
    """أمر: إضافة تفسير — يعرض واجهة اختيار السورة ثم يحدد الآية تلقائياً"""
    if (message.text or "").strip() != "إضافة تفسير":
        return False

    if not is_any_dev(message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return True

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    sent = send_ui(
        cid,
        text="📝 <b>إضافة تفسير</b>\n\nاختر السورة:",
        buttons=[btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)],
        layout=[1],
        owner_id=uid,
        reply_to=message.message_id,
    )
    if sent:
        import types as _types
        fake_call = _types.SimpleNamespace(
            from_user=message.from_user,
            message=sent,
        )
        from modules.quran.sura_selector import show_sura_selector
        show_sura_selector(
            fake_call, 0,
            callback_action="qr_dev_tafseer_select_sura",
            cancel_action="qr_dev_cancel",
            page_action="qr_dev_tafseer_sura_page",
            title="📝 إضافة تفسير — اختر السورة",
            suras_source="with_ayat",
            edit=True,
        )
    return True


@register_action("qr_dev_tafseer_select_sura")
def on_select_sura(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    sura_id = data.get("sura_id")
    sura = db.get_sura(sura_id)
    if not sura:
        bot.answer_callback_query(call.id, "❌ السورة غير موجودة.", show_alert=True)
        return

    ayat = db.get_ayat_by_sura(sura_id)
    if not ayat:
        bot.answer_callback_query(call.id, f"❌ لا توجد آيات في سورة {sura['name']}.", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    # ترتيب التفسير: الميسر → السعدي → المختصر
    TAFSEER_ORDER = [
        ("الميسر",   "tafseer_muyassar"),
        ("السعدي",   "tafseer_saadi"),
        ("المختصر",  "tafseer_mukhtasar"),
    ]

    owner = (uid, cid)
    buttons = []
    for name_ar, col in TAFSEER_ORDER:
        next_ayah = db.get_next_tafseer_ayah(sura_id, col)
        buttons.append(btn(
            f"{name_ar} (من آية {next_ayah})",
            "qr_dev_tafseer_select_type",
            {"sura_id": sura_id, "type": name_ar, "start": next_ayah},
            color=_B, owner=owner,
        ))
    buttons.append(btn("🔙 رجوع للسور", "qr_dev_tafseer_back_to_suras", {}, color=_R, owner=owner))

    try:
        bot.edit_message_text(
            f"📝 <b>إضافة تفسير</b>\n<b>السورة:</b> {sura['name']}\n\n"
            f"اختر نوع التفسير:\n<i>الرقم بجانب كل تفسير هو الآية التالية التي تحتاج تفسيراً</i>",
            cid, call.message.message_id, parse_mode="HTML",
            reply_markup=build_keyboard(buttons, [3, 1], uid),
        )
    except Exception:
        pass


@register_action("qr_dev_tafseer_select_type")
def on_select_tafseer_type(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    sura_id      = data.get("sura_id")
    tafseer_type = data.get("type")
    start_ayah   = int(data.get("start", 1))
    sura         = db.get_sura(sura_id)

    if not sura or tafseer_type not in db.TAFSEER_TYPES:
        bot.answer_callback_query(call.id, "❌ خطأ في البيانات.", show_alert=True)
        return

    set_state(uid, cid, "qr_dev_tafseer_bulk_content",
              {"sura_id": sura_id, "type": tafseer_type, "start": start_ayah,
               "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)

    text = (
        f"📚 <b>إضافة تفسير {tafseer_type}</b>\n"
        f"<b>السورة:</b> {sura['name']}\n"
        f"<b>تبدأ من آية:</b> {start_ayah}\n\n"
        f"أرسل التفاسير مفصولة بـ:\n<code>{db.BULK_SEPARATOR}</code>\n\n"
        f"مثال:\nتفسير آية {start_ayah}\n{db.BULK_SEPARATOR}\nتفسير آية {start_ayah + 1}"
    )
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=(uid, cid))
    try:
        bot.edit_message_text(text, cid, call.message.message_id, parse_mode="HTML",
                             reply_markup=build_keyboard([cancel_btn], [1], uid))
    except Exception:
        pass


@register_action("qr_dev_tafseer_sura_page")
def on_sura_page(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    page = int(data.get("p", 0))
    bot.answer_callback_query(call.id)
    from modules.quran.sura_selector import show_sura_selector
    show_sura_selector(
        call, page,
        callback_action=data.get("act", "qr_dev_tafseer_select_sura"),
        cancel_action=data.get("cact", "qr_dev_cancel"),
        page_action=data.get("pact", "qr_dev_tafseer_sura_page"),
        title="📝 إضافة تفسير — اختر السورة",
        suras_source="with_ayat",
        edit=True,
    )


@register_action("qr_dev_tafseer_back_to_suras")
def on_back_to_suras(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    from modules.quran.sura_selector import show_sura_selector
    show_sura_selector(
        call, 0,
        callback_action="qr_dev_tafseer_select_sura",
        cancel_action="qr_dev_cancel",
        page_action="qr_dev_tafseer_sura_page",
        title="📝 إضافة تفسير — اختر السورة",
        suras_source="with_ayat",
        edit=True,
    )


# ══════════════════════════════════════════
# نقطة الدخول الموحدة
# ══════════════════════════════════════════

def handle_quran_commands(message) -> bool:
    """
    يعالج كل أوامر القرآن.
    يرجع True إذا تم التعامل مع الأمر.
    """
    text = (message.text or "").strip()

    if text == "تلاوة":
        return handle_tilawa(message)
    if text == "مسح تلاوتي":
        return handle_reset(message)
    if text == "مفضلتي":
        return handle_my_favorites(message)
    if text == "إضافة تفسير":
        return handle_add_tafseer(message)
    if text == "إضافة آيات":
        return handle_add_ayat(message)
    if text == "قراءة سورة":
        from modules.quran.surah_reader import handle_surah_read_command
        return handle_surah_read_command(message)
    if text == "ختمتي":
        from modules.quran.khatmah import handle_khatmah_read_command
        return handle_khatmah_read_command(message)
    if text in ["إعدادات ختمة", "اعدادات ختمة"]:
        from modules.quran.khatmah import handle_khatmah_settings_command
        return handle_khatmah_settings_command(message)
    if text == "تذكير ختمتي":
        from modules.quran.khatmah import handle_khatmah_reminder_command
        return handle_khatmah_reminder_command(message)
    if text.startswith("آية "):
        return handle_search(message)
    if is_any_dev(message.from_user.id):
        if (text.startswith("اضف آيات ") or
                text.startswith("عدل آية ") or
                text.startswith("عدل تفسير ")):
            return handle_dev_quran_command(message)
    return False

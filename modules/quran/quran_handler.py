"""
modules/quran/quran_handler.py
────────────────────────────────
معالج نظام القرآن — التفاعل مع البوت فقط.

الميزات المدعومة:
  - ختمتي / إعدادات ختمة / تذكير ختمتي  (khatmah.py)
  - قراءة سورة                            (surah_reader.py)
  - مفضلتي                                (favorites)
  - آية [بحث]                             (search)
  - إضافة آيات / إضافة تفسير             (dev — content management)
  - اضف آيات / عدل آية / عدل تفسير       (dev — text commands)

NOTE: "تلاوة" and "مسح تلاوتي" are intentionally removed.
      Favorites and search are independent features — NOT tilawa.
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
# 🔙 Navigation callbacks (used by search & favorites)
# ══════════════════════════════════════════

def _send_ayah(uid: int, cid: int, ayah: dict,
               edit_call=None, reply_to: int = None,
               source: str = None, fav_page: int = 0,
               with_tashkeel: bool = True):
    """يرسل أو يعدّل رسالة الآية — مستخدمة من البحث والمفضلة."""
    total    = db.get_total_ayat()
    is_fav   = db.is_favorite(uid, ayah["id"])
    has_prev = db.get_prev_ayah(ayah["id"]) is not None
    has_next = db.get_next_ayah(ayah["id"]) is not None

    text, (buttons, layout) = (
        ui.build_ayah_text(ayah, total, with_tashkeel=with_tashkeel),
        ui.build_ayah_buttons(uid, cid, ayah, is_fav, has_prev, has_next,
                              source=source, fav_page=fav_page),
    )

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("qr_next")
def on_next(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    wt   = bool(int(data.get("wt", 1)))
    ayah = db.get_next_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "✅ وصلت لآخر آية!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0),
               with_tashkeel=wt)


@register_action("qr_prev")
def on_prev(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    wt   = bool(int(data.get("wt", 1)))
    ayah = db.get_prev_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "⬅️ هذه أول آية.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0),
               with_tashkeel=wt)


@register_action("qr_goto_ayah")
def on_goto(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    wt   = bool(int(data.get("wt", 1)))
    ayah = db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0),
               with_tashkeel=wt)


@register_action("qr_back_to_ayah")
def on_back_to_ayah(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    wt   = bool(int(data.get("wt", 1)))
    ayah = db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_ayah(uid, cid, ayah, edit_call=call,
               source=data.get("src"), fav_page=data.get("fp", 0),
               with_tashkeel=wt)


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
    wt  = bool(int(data.get("wt", 1)))

    is_now_fav, msg = svc.toggle_favorite(uid, aid)
    bot.answer_callback_query(call.id, msg, show_alert=False)

    ayah = db.get_ayah(aid)
    if ayah:
        _send_ayah(uid, cid, ayah, edit_call=call,
                   source=data.get("src"), fav_page=data.get("fp", 0),
                   with_tashkeel=wt)


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

    # Fetch preference once at session start
    from modules.quran.tashkeel_pref import get_pref
    with_tashkeel = get_pref(uid, "ayah_search")

    _show_favorites(uid, cid, favs, page=0, reply_to=message.message_id,
                    with_tashkeel=with_tashkeel)
    return True


def _show_favorites(uid: int, cid: int, favs: list,
                    page: int, reply_to: int = None, edit_call=None,
                    with_tashkeel: bool = True):
    items, total_pages = paginate_list(favs, page, per_page=_PER_PAGE)
    text    = ui.build_favorites_text(items, page, total_pages,
                                      with_tashkeel=with_tashkeel)
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
    from modules.quran.tashkeel_pref import get_pref
    _show_favorites(uid, cid, favs, page, edit_call=call,
                    with_tashkeel=get_pref(uid, "ayah_search"))


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
    from modules.quran.tashkeel_pref import get_pref
    _show_favorites(uid, cid, favs, page, edit_call=call,
                    with_tashkeel=get_pref(uid, "ayah_search"))


@register_action("qr_fav_clear_prompt")
def on_fav_clear_prompt(call, data):
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
    uid  = call.from_user.id
    cid  = call.message.chat.id
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
    _show_favorites(uid, cid, favs, page, edit_call=call)


# ══════════════════════════════════════════
# 📖 التفسير (مستخدم من البحث والمفضلة)
# ══════════════════════════════════════════

@register_action("qr_tafseer")
def on_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    wt   = bool(int(data.get("wt", 1)))
    ayah = db.get_ayah(aid)

    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    available = svc.get_available_tafseer(ayah)
    if not available:
        bot.answer_callback_query(call.id, "لم يتم إضافة تفسير بعد لهذه الآية",
                                  show_alert=True)
        return

    sura      = db.get_sura(ayah["sura_id"])
    sura_name = sura["name"] if sura else f"سورة {ayah['sura_id']}"
    source    = data.get("src")
    fav_page  = data.get("fp", 0)

    from modules.quran.tashkeel_pref import apply_pref
    ayah_text = apply_pref(ayah["text_with_tashkeel"], wt)

    buttons, layout = ui.build_tafseer_buttons(uid, cid, ayah,
                                               source=source, fav_page=fav_page,
                                               with_tashkeel=wt)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"📖 <b>{sura_name}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n"
                f"{ayah_text}\n\n"
                f"{get_lines()}\n"
                f"اختر التفسير:"
            ),
            buttons=buttons, layout=layout)


@register_action("qr_show_tafseer")
def on_show_tafseer(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    aid  = data.get("aid")
    col  = data.get("col")
    wt   = bool(int(data.get("wt", 1)))
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

    from modules.quran.tashkeel_pref import apply_pref
    ayah_text = apply_pref(ayah["text_with_tashkeel"], wt)

    back_ctx = {"aid": aid, "wt": int(wt)}
    if source:
        back_ctx["src"] = source
        back_ctx["fp"]  = fav_page

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"📖 <b>تفسير {name_ar}</b>\n"
                f"<b>{sura_name}</b> — آية {ayah['ayah_number']}\n"
                f"{get_lines()}\n\n"
                f"{ayah_text}\n\n"
                f"{get_lines()}\n"
                f"📝 <b>التفسير:</b>\n{content}"
            ),
            buttons=[btn("🔙 رجوع للتفاسير", "qr_tafseer", back_ctx,
                         color=_R, owner=owner)],
            layout=[1])


# ══════════════════════════════════════════
# 🔍 البحث في القرآن
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

    uid            = message.from_user.id
    cid            = message.chat.id
    results, total = svc.search(query)

    if not results:
        bot.reply_to(message,
                     f"🔍 لم يتم العثور على نتائج لـ: <b>{query}</b>",
                     parse_mode="HTML")
        return True

    # Fetch preference once at session start
    from modules.quran.tashkeel_pref import get_pref
    with_tashkeel = get_pref(uid, "ayah_search")

    _show_search_results(uid, cid, query, results, total,
                         page=0, reply_to=message.message_id,
                         with_tashkeel=with_tashkeel)
    return True


def _show_search_results(uid: int, cid: int, query: str,
                          results: list, total_occurrences: int,
                          page: int, reply_to: int = None, edit_call=None,
                          with_tashkeel: bool = True):
    items, total_pages = paginate_list(results, page, per_page=_PER_PAGE)
    text    = ui.build_search_result_text(items, page, total_pages,
                                          query=query,
                                          ayat_count=len(results),
                                          total_occurrences=total_occurrences,
                                          with_tashkeel=with_tashkeel)
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
    from modules.quran.tashkeel_pref import get_pref
    _show_search_results(uid, cid, query, results, total, page, edit_call=call,
                         with_tashkeel=get_pref(uid, "ayah_search"))

def handle_dev_quran_input(message) -> bool:
    """
    يعالج حالات الانتظار الخاصة بإدارة القرآن.
    يرجع True إذا تم التعامل مع الرسالة.

    Only handles states whose type starts with "qr_dev_".
    Uses StateManager.is_state to avoid intercepting other features' states.
    """
    uid = message.from_user.id
    cid = message.chat.id

    if not is_any_dev(uid):
        return False

    # Use StateManager directly — only claim qr_dev_* states
    from core.state_manager import StateManager
    current = StateManager.get(uid, cid)
    if not current:
        return False

    s = current.get("type", "")
    if not s.startswith("qr_dev_"):
        return False

    # Reconstruct sdata from StateManager format for backward-compat
    sdata = dict(current.get("extra") or {})
    if current.get("mid") is not None:
        sdata["_mid"] = current["mid"]
    if current.get("step") is not None:
        sdata["_step"] = current["step"]

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
    # Clear only this feature's state — never touch other features' states
    StateManager.clear_if_type(uid, cid, s)

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
    uid  = message.from_user.id
    cid  = message.chat.id

    if text == "مفضلتي":
        return handle_my_favorites(message)
    if text.startswith("آية "):
        return handle_search(message)
    if text == "إضافة تفسير":
        return handle_add_tafseer(message)
    if text == "إضافة آيات":
        return handle_add_ayat(message)
    if text == "قراءة سورة":
        # Clear only read_surah state — never touch khatmah state
        from core.state_manager import StateManager
        StateManager.clear_if_type(uid, cid, "read_surah_flow")
        from modules.quran.surah_reader import handle_surah_read_command
        return handle_surah_read_command(message)
    if text == "ختمتي":
        # Clear only khatma state — never touch read_surah state
        from core.state_manager import StateManager
        StateManager.clear_if_type(uid, cid, "khatma_flow")
        from modules.quran.khatmah import handle_khatmah_read_command
        return handle_khatmah_read_command(message)
    if text in ["إعدادات ختمة", "اعدادات ختمة"]:
        from modules.quran.khatmah import handle_khatmah_settings_command
        return handle_khatmah_settings_command(message)
    if text == "تذكير ختمتي":
        from modules.quran.khatmah import handle_khatmah_reminder_command
        return handle_khatmah_reminder_command(message)
    if text == "تشكيل الآيات":
        from modules.quran.tashkeel_pref import handle_tashkeel_command
        return handle_tashkeel_command(message)
    if is_any_dev(message.from_user.id):
        if (text.startswith("اضف آيات ") or
                text.startswith("عدل آية ") or
                text.startswith("عدل تفسير ")):
            return handle_dev_quran_command(message)
    return False

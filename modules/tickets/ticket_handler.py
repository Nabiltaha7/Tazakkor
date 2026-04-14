"""
modules/tickets/ticket_handler.py
───────────────────────────────────
معالج التذاكر — منطق الأعمال الأساسي

الحالات (StateManager):
  type="ticket_flow"  step="await_category"  — انتظار اختيار الفئة
  type="ticket_flow"  step="await_msg"       — انتظار رسالة التذكرة
  type="ticket_flow"  step="await_confirm"   — انتظار تأكيد الإرسال
  type="dev_reply"    extra={"tid": id}      — انتظار رد المطور
"""
import time
from core.bot import bot
from core.config import developers_id
from core.dev_notifier import send_to_dev_group
from core.state_manager import StateManager
from utils.helpers import get_lines
from modules.tickets.ticket_db import (
    create_ticket, get_ticket, get_open_ticket_for_user,
    add_ticket_message, close_ticket, set_ticket_group_msg,
    get_ticket_by_group_msg, check_limits, record_ticket_usage,
    is_ticket_banned,
)
from database.db_queries.reports_queries import is_developer
from core.admin import get_const_int

_TICKET_TTL = 600   # 10 دقائق


def _get_dev_group_id() -> int:
    return get_const_int("dev_group_id", -1)


DEVELOPERS = list(developers_id)

CATEGORIES = {
    "bug":        "🐞 خطأ برمجي",
    "suggestion": "💡 اقتراح",
    "complaint":  "🚫 شكوى",
}


# ══════════════════════════════════════════
# 🎫 بدء إنشاء تذكرة
# ══════════════════════════════════════════

def start_ticket_flow(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.sticker:
        bot.reply_to(message, "❌ لا يمكن إرسال ملصقات كتذكرة.")
        return

    if is_ticket_banned(user_id):
        bot.reply_to(message,
                     "🚫 <b>تم تقييد وصولك لنظام التذاكر</b>\n\n"
                     "لا يمكنك إرسال تقارير في الوقت الحالي.",
                     parse_mode="HTML")
        return

    ok, err = check_limits(user_id)
    if not ok:
        bot.reply_to(message, err)
        return

    StateManager.set(user_id, chat_id, {
        "type": "ticket_flow",
        "step": "await_category",
        "extra": {},
    }, ttl=_TICKET_TTL)

    from utils.pagination import btn, send_ui
    buttons = [
        btn("🐞 خطأ برمجي", "ticket_cat", {"cat": "bug"},        owner=(user_id, chat_id), color="d"),
        btn("💡 اقتراح",     "ticket_cat", {"cat": "suggestion"}, owner=(user_id, chat_id), color="su"),
        btn("🚫 شكوى",       "ticket_cat", {"cat": "complaint"},  owner=(user_id, chat_id), color="p"),
    ]
    msg = send_ui(chat_id,
                  text="🎫 <b>إنشاء تذكرة جديدة</b>\n\nاختر نوع التذكرة:",
                  buttons=buttons, layout=[1, 1, 1], owner_id=user_id,
                  reply_to=message.message_id)
    if msg:
        StateManager.set_mid(user_id, chat_id, msg.message_id)


def handle_category_selection(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    cat     = data.get("cat")

    if cat not in CATEGORIES:
        bot.answer_callback_query(call.id, "❌ فئة غير صالحة", show_alert=True)
        return

    StateManager.update(user_id, chat_id, {
        "step":  "await_msg",
        "extra": {"cat": cat},
    })
    StateManager.set_mid(user_id, chat_id, call.message.message_id)
    bot.answer_callback_query(call.id)

    from utils.pagination import btn, edit_ui
    from utils.pagination.buttons import build_keyboard
    cancel_btn = btn("❌ إلغاء", "ticket_cancel_send", {}, owner=(user_id, chat_id), color="d")
    try:
        bot.edit_message_text(
            f"🎫 <b>تذكرة جديدة — {CATEGORIES[cat]}</b>\n\n"
            f"✏️ أرسل رسالتك الآن (نص، صورة، أو فيديو):",
            chat_id, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], user_id),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 📨 استقبال رسالة التذكرة
# ══════════════════════════════════════════

def handle_ticket_message_input(message) -> bool:
    user_id = message.from_user.id
    chat_id = message.chat.id

    state = StateManager.get(user_id, chat_id)
    if not state or state.get("type") != "ticket_flow":
        return False
    if state.get("step") != "await_msg":
        return False

    if _is_unsupported_media(message):
        bot.reply_to(message,
                     "❌ <b>نوع الرسالة غير مدعوم</b>\n\n"
                     "يمكنك إرسال: نص، صورة، أو فيديو فقط.",
                     parse_mode="HTML")
        return True

    if (message.photo or message.video) and message.caption:
        if len(message.caption) > 1024:
            bot.reply_to(message,
                         f"❌ التعليق طويل جداً (الحد 1024 حرف، لديك {len(message.caption)}).",
                         parse_mode="HTML")
            return True

    cat   = state.get("extra", {}).get("cat", "bug")
    mid   = state.get("mid")

    # حفظ الرسالة في extra وانتقل لخطوة التأكيد
    StateManager.update(user_id, chat_id, {
        "step":  "await_confirm",
        "extra": {
            "cat":            cat,
            "msg_id":         message.message_id,
            "msg_type":       _get_msg_type(message),
            "content":        _get_content(message),
            "file_id":        _get_file_id(message),
            "file_unique_id": _get_file_unique_id(message),
        },
    })

    _show_confirm_ui(user_id, chat_id, message, cat, mid)
    return True


def _show_confirm_ui(user_id, chat_id, message, cat, mid=None):
    from utils.pagination import btn, send_ui, edit_ui
    from utils.pagination.buttons import build_keyboard

    if message.photo:
        preview = f"🖼 صورة" + (f" — {message.caption[:60]}" if message.caption else "")
    elif message.video:
        preview = f"🎥 فيديو" + (f" — {message.caption[:60]}" if message.caption else "")
    else:
        t = message.text or ""
        preview = f"💬 {t[:80]}{'...' if len(t) > 80 else ''}"

    text = (
        f"📋 <b>مراجعة التذكرة قبل الإرسال</b>\n\n"
        f"📂 النوع: {CATEGORIES[cat]}\n"
        f"📩 المحتوى: {_escape(preview)}\n\n"
        f"هل تريد إرسال هذه التذكرة للمطور؟"
    )
    owner   = (user_id, chat_id)
    buttons = [
        btn("✅ إرسال", "ticket_confirm_send", {}, owner=owner, color="su"),
        btn("❌ إلغاء", "ticket_cancel_send",  {}, owner=owner, color="d"),
    ]

    if mid:
        try:
            bot.edit_message_text(
                text, chat_id, mid,
                parse_mode="HTML",
                reply_markup=build_keyboard(buttons, [2], user_id),
            )
            return
        except Exception:
            pass

    msg = send_ui(chat_id, text=text, buttons=buttons, layout=[2], owner_id=user_id)
    if msg:
        StateManager.set_mid(user_id, chat_id, msg.message_id)


# ══════════════════════════════════════════
# ✅ تأكيد الإرسال
# ══════════════════════════════════════════

def confirm_and_send_ticket(user_id: int, chat_id: int):
    """
    يُنشئ التذكرة ويرسلها للمجموعة.
    يرجع (True, ticket_id) أو (False, None).
    """
    state = StateManager.get(user_id, chat_id)
    if not state or state.get("type") != "ticket_flow":
        return False, None
    if state.get("step") != "await_confirm":
        return False, None

    extra = state.get("extra", {})
    cat   = extra.get("cat", "bug")

    StateManager.clear(user_id, chat_id)

    ticket_id = create_ticket(user_id, chat_id, cat)
    record_ticket_usage(user_id)

    add_ticket_message(
        ticket_id, "user",
        extra.get("msg_id"),
        extra.get("msg_type", "text"),
        extra.get("content"),
        extra.get("file_id"),
        extra.get("file_unique_id"),
    )

    group_msg_id = _send_to_devs_from_extra(ticket_id, user_id, extra, cat)
    if group_msg_id:
        set_ticket_group_msg(ticket_id, group_msg_id)

    return True, ticket_id


def cancel_pending_ticket(user_id: int, chat_id: int = None):
    """يُلغي التذكرة المعلقة."""
    if chat_id:
        StateManager.clear_if_type(user_id, chat_id, "ticket_flow")
    else:
        # fallback: مسح من أي محادثة (نادر)
        pass


# ══════════════════════════════════════════
# 📤 إرسال للمجموعة
# ══════════════════════════════════════════

def _send_to_devs_from_extra(ticket_id: int, user_id: int,
                              extra: dict, cat: str) -> int | None:
    """يرسل التذكرة لمجموعة المطورين باستخدام البيانات المحفوظة في extra."""
    try:
        user_obj = bot.get_chat(user_id)
        first    = user_obj.first_name or ""
    except Exception:
        first = str(user_id)

    mention = f'<a href="tg://user?id={user_id}">{_escape(first)}</a>'
    dev_id  = list(developers_id)[0]
    try:
        dev_obj  = bot.get_chat(dev_id)
        dev_name = f"{dev_obj.first_name or ''} {dev_obj.last_name or ''}".strip()
    except Exception:
        dev_name = "المطور"

    line   = get_lines()
    header = (
        f"تعال <a href='tg://user?id={dev_id}'><b>{dev_name}</b></a>\n"
        f"{line}\n"
        f"🎫 <b>تذكرة جديدة #{ticket_id}</b>\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📂 النوع: {CATEGORIES.get(cat, cat)}\n"
        f"{line}\n📩 الرسالة:\n"
    )

    from utils.pagination import btn
    from utils.pagination.buttons import build_keyboard
    buttons = [
        btn("💬 رد",            "ticket_dev_reply", {"tid": ticket_id}, owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close",     {"tid": ticket_id}, owner=None, color="d"),
        btn("🚫 حظر المستخدم",  "ticket_ban_user",  {"uid": user_id},   owner=None, color="d"),
    ]
    markup       = build_keyboard(buttons, [2, 1], None)
    dev_group_id = _get_dev_group_id()
    msg_type     = extra.get("msg_type", "text")
    content      = extra.get("content") or ""
    file_id      = extra.get("file_id")

    try:
        if msg_type == "photo" and file_id:
            caption = header + _escape(content) + f"\n{line}"
            sent = bot.send_photo(dev_group_id, file_id,
                                  caption=caption, parse_mode="HTML",
                                  reply_markup=markup)
        elif msg_type == "video" and file_id:
            caption = header + _escape(content) + f"\n{line}"
            sent = bot.send_video(dev_group_id, file_id,
                                  caption=caption, parse_mode="HTML",
                                  reply_markup=markup)
        else:
            msg_id = send_to_dev_group(
                header + _escape(content) + f"\n{line}",
                reply_markup=markup,
            )
            return msg_id
        return sent.message_id if sent else None
    except Exception as e:
        print(f"[Tickets] خطأ إرسال للمجموعة: {e}")
        return None


def send_to_devs(ticket_id, message, cat):
    """واجهة متوافقة مع الكود القديم — تُستخدم عند توفر كائن message."""
    user    = message.from_user
    mention = f'<a href="tg://user?id={user.id}">{_escape(user.first_name)}</a>'
    dev_id  = list(developers_id)[0]
    try:
        dev_obj  = bot.get_chat(dev_id)
        dev_name = f"{dev_obj.first_name or ''} {dev_obj.last_name or ''}".strip()
    except Exception:
        dev_name = "المطور"

    line   = get_lines()
    header = (
        f"تعال <a href='tg://user?id={dev_id}'><b>{dev_name}</b></a>\n"
        f"{line}\n"
        f"🎫 <b>تذكرة جديدة #{ticket_id}</b>\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📂 النوع: {CATEGORIES.get(cat, cat)}\n"
        f"{line}\n📩 الرسالة:\n"
    )

    from utils.pagination import btn
    from utils.pagination.buttons import build_keyboard
    buttons = [
        btn("💬 رد",            "ticket_dev_reply", {"tid": ticket_id},            owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close",     {"tid": ticket_id},            owner=None, color="d"),
        btn("🚫 حظر المستخدم",  "ticket_ban_user",  {"uid": message.from_user.id}, owner=None, color="d"),
    ]
    markup       = build_keyboard(buttons, [2, 1], None)
    dev_group_id = _get_dev_group_id()

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = header + (_escape(message.caption) if message.caption else "") + f"\n{line}"
        try:
            sent = bot.send_photo(dev_group_id, file_id, caption=caption,
                                  parse_mode="HTML", reply_markup=markup)
            return sent.message_id
        except Exception as e:
            print(f"[Tickets] خطأ إرسال صورة: {e}")
            return None
    if message.video:
        file_id = message.video.file_id
        caption = header + (_escape(message.caption) if message.caption else "") + f"\n{line}"
        try:
            sent = bot.send_video(dev_group_id, file_id, caption=caption,
                                  parse_mode="HTML", reply_markup=markup)
            return sent.message_id
        except Exception as e:
            print(f"[Tickets] خطأ إرسال فيديو: {e}")
            return None
    return send_to_dev_group(
        header + _escape(message.text or "") + f"\n{line}",
        reply_markup=markup,
    )


# ══════════════════════════════════════════
# 💬 رد المطور
# ══════════════════════════════════════════

def set_awaiting_dev_reply(user_id: int, ticket_id: int):
    """يضع المطور في حالة انتظار الرد على تذكرة."""
    StateManager.set(user_id, _get_dev_group_id(), {
        "type":  "dev_reply",
        "step":  "await_reply",
        "extra": {"tid": ticket_id},
    }, ttl=300)


def handle_dev_reply(message) -> bool:
    user_id = message.from_user.id
    chat_id = message.chat.id

    if chat_id != _get_dev_group_id():
        return False
    if not is_developer(user_id):
        return False

    ticket_id = None

    # طريقة 1: رد على رسالة التذكرة
    if message.reply_to_message:
        ticket = get_ticket_by_group_msg(message.reply_to_message.message_id)
        if ticket:
            ticket_id = ticket["id"]

    # طريقة 2: StateManager
    if not ticket_id:
        state = StateManager.get(user_id, chat_id)
        if state and state.get("type") == "dev_reply":
            ticket_id = state.get("extra", {}).get("tid")
            StateManager.clear(user_id, chat_id)

    if not ticket_id:
        return False

    ticket = get_ticket(ticket_id)
    if not ticket:
        return False
    if ticket["status"] == "closed":
        bot.reply_to(message, "❌ هذه التذكرة مغلقة.")
        return True
    if _is_unsupported_media(message):
        return False

    msg_type, content, file_id, file_unique_id = _extract_message_info(message)
    add_ticket_message(ticket_id, "developer", message.message_id,
                       msg_type, content, file_id, file_unique_id)
    _send_dev_reply_to_user(ticket, message, ticket_id)
    bot.reply_to(message, f"✅ تم إرسال ردك للمستخدم (تذكرة #{ticket_id})")
    return True


def _send_dev_reply_to_user(ticket, message, ticket_id):
    user_id = ticket["user_id"]
    dev     = message.from_user
    mention = f'<a href="tg://user?id={dev.id}">{_escape(dev.first_name)}</a>'
    header  = (
        f"💬 <b>رد المطور على تذكرتك #{ticket_id}</b>\n"
        f"👤 {mention}\n{get_lines()}\n✉️ الرد:\n"
    )
    try:
        if message.photo:
            bot.send_photo(user_id, message.photo[-1].file_id,
                           caption=header + (_escape(message.caption) or "") + f"\n{get_lines()}",
                           parse_mode="HTML")
        elif message.video:
            bot.send_video(user_id, message.video.file_id,
                           caption=header + (_escape(message.caption) or "") + f"\n{get_lines()}",
                           parse_mode="HTML")
        elif message.text:
            bot.send_message(user_id,
                             header + _escape(message.text) + f"\n{get_lines()}",
                             parse_mode="HTML")
    except Exception as e:
        print(f"[Tickets] خطأ إرسال رد للمستخدم: {e}")


# ══════════════════════════════════════════
# 👤 رد المستخدم على تذكرة مفتوحة
# ══════════════════════════════════════════

def handle_user_followup(message) -> bool:
    user_id = message.from_user.id
    if message.chat.type != "private":
        return False

    ticket = get_open_ticket_for_user(user_id)
    if not ticket:
        return False
    if _is_unsupported_media(message):
        return False

    ticket_id = ticket["id"]
    msg_type, content, file_id, file_unique_id = _extract_message_info(message)
    add_ticket_message(ticket_id, "user", message.message_id,
                       msg_type, content, file_id, file_unique_id)
    _forward_user_reply_to_devs(ticket, message, ticket_id)

    from utils.helpers import send_with_delay
    send_with_delay(message.chat.id,
                    f"📨 تم إرسال رسالتك للمطور (تذكرة #{ticket_id}) ✅",
                    delay=0.4, reply_to=message.message_id)
    return True


def _forward_user_reply_to_devs(ticket, message, ticket_id):
    user    = message.from_user
    mention = f'<a href="tg://user?id={user.id}">{_escape(user.first_name)}</a>'
    header  = (
        f"🎫 <b>رد على التذكرة #{ticket_id}</b>\n"
        f"👤 المستخدم: {mention}\n{get_lines()}\n📩 الرسالة:\n"
    )
    from utils.pagination import btn
    from utils.pagination.buttons import build_keyboard
    buttons = [
        btn("💬 رد",            "ticket_dev_reply", {"tid": ticket_id},         owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close",     {"tid": ticket_id},         owner=None, color="d"),
        btn("🚫 حظر المستخدم",  "ticket_ban_user",  {"uid": ticket["user_id"]}, owner=None, color="d"),
    ]
    markup       = build_keyboard(buttons, [2, 1], None)
    dev_group_id = _get_dev_group_id()

    if message.photo:
        try:
            bot.send_photo(dev_group_id, message.photo[-1].file_id,
                           caption=header + (_escape(message.caption) or "") + f"\n{get_lines()}",
                           parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"[Tickets] خطأ إعادة توجيه صورة: {e}")
    elif message.video:
        try:
            bot.send_video(dev_group_id, message.video.file_id,
                           caption=header + (_escape(message.caption) or "") + f"\n{get_lines()}",
                           parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"[Tickets] خطأ إعادة توجيه فيديو: {e}")
    elif message.text:
        send_to_dev_group(
            header + _escape(message.text) + f"\n{get_lines()}",
            reply_markup=markup,
        )


# ══════════════════════════════════════════
# 🔒 إغلاق التذكرة
# ══════════════════════════════════════════

def close_ticket_action(ticket_id: int, closer_user_id: int):
    if not is_developer(closer_user_id):
        return False, "❌ فقط المطورون يمكنهم إغلاق التذاكر."
    ticket = get_ticket(ticket_id)
    if not ticket:
        return False, "❌ التذكرة غير موجودة."
    if ticket["status"] == "closed":
        return False, "❌ التذكرة مغلقة بالفعل."

    close_ticket(ticket_id)
    try:
        from utils.helpers import send_with_delay
        send_with_delay(
            ticket["user_id"],
            f"🔒 <b>تم إغلاق التذكرة #{ticket_id}</b>\n\n"
            f"شكراً لتواصلك معنا. نتمنى أن نكون قد أفدناك 🙆‍♂",
            delay=0.5
        )
    except Exception:
        pass
    return True, f"✅ تم إغلاق التذكرة #{ticket_id}"


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def _get_msg_type(message) -> str:
    if message.photo:  return "photo"
    if message.video:  return "video"
    if message.text:   return "text"
    return "unknown"

def _get_content(message) -> str | None:
    if message.photo or message.video:
        return (message.caption or "")[:500]
    if message.text:
        return message.text[:500]
    return None

def _get_file_id(message) -> str | None:
    if message.photo: return message.photo[-1].file_id
    if message.video: return message.video.file_id
    return None

def _get_file_unique_id(message) -> str | None:
    if message.photo: return message.photo[-1].file_unique_id
    if message.video: return message.video.file_unique_id
    return None

def _extract_message_info(message):
    return (
        _get_msg_type(message),
        _get_content(message),
        _get_file_id(message),
        _get_file_unique_id(message),
    )

def _is_unsupported_media(message) -> bool:
    return bool(
        message.sticker or message.audio or message.voice or
        message.video_note or message.document or message.animation
    )

def _escape(text) -> str:
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

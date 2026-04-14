"""
modules/azkar/azkar_handler.py
────────────────────────────────
معالج الأذكار للمستخدمين

الأوامر المدعومة:
  أذكار الصباح    → zikr_type = 0
  أذكار المساء    → zikr_type = 1
  أذكار النوم     → zikr_type = 2
  أذكار الاستيقاظ → zikr_type = 3

التدفق:
  1. المستخدم يرسل الأمر
  2. البوت يعرض الذكر الأول مع زر "✅ التالي"
  3. كل ضغطة تنقل للذكر التالي (مع احتساب التكرار)
  4. عند الانتهاء: رسالة إتمام مع زر إعادة البدء

التقدم محفوظ في قاعدة البيانات (azkar_progress) —
يمكن للمستخدم الإيقاف والاستئناف لاحقاً.
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from database.db_queries.azkar_queries import (
    get_azkar_list,
    get_azkar_progress,
    save_azkar_progress,
    reset_azkar_progress,
    zikr_exists,
)

# ── خريطة الأوامر → zikr_type ──────────────────────────────────────
_COMMANDS: dict[str, int] = {
    "أذكار الصباح":    0,
    "أذكار المساء":    1,
    "أذكار النوم":     2,
    "أذكار الاستيقاظ": 3,
}

_LABELS = {
    0: ("🌅", "أذكار الصباح"),
    1: ("🌙", "أذكار المساء"),
    2: ("😴", "أذكار النوم"),
    3: ("☀️", "أذكار الاستيقاظ"),
}

_B = "p"
_G = "su"
_R = "d"


# ══════════════════════════════════════════
# نقطة الدخول — أوامر المستخدم
# ══════════════════════════════════════════

def handle_azkar_command(message) -> bool:
    """يعالج أوامر الأذكار النصية. يرجع True إذا تم التعامل مع الأمر."""
    text = (message.text or "").strip()
    zikr_type = _COMMANDS.get(text)
    if zikr_type is None:
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if not zikr_exists(zikr_type):
        bot.reply_to(message,
                     "⚠️ لا توجد أذكار مضافة بعد لهذه الفئة.",
                     parse_mode="HTML")
        return True

    _start_session(uid, cid, zikr_type, reply_to=message.message_id)
    return True


def handle_azkar_input(message) -> bool:
    """
    معالج الإدخال النصي — غير مطلوب حالياً لأن الجلسة تعمل بالأزرار.
    محجوز للتوسع المستقبلي (مثل إدخال رقم الذكر يدوياً).
    """
    return False


def open_azkar_admin(message) -> None:
    """يفتح لوحة إدارة الأذكار للمطورين — يُحوَّل للوحة الإدارة الرئيسية."""
    from handlers.group_admin.developer.admin_panel import open_admin_panel
    open_admin_panel(message)


# ══════════════════════════════════════════
# منطق الجلسة
# ══════════════════════════════════════════

def _start_session(uid: int, cid: int, zikr_type: int,
                   reply_to: int = None, call=None) -> None:
    """يبدأ جلسة أذكار من أول ذكر (أو يستأنف من حيث توقف)."""
    azkar = get_azkar_list(zikr_type)
    if not azkar:
        _reply_or_edit(cid, uid, "⚠️ لا توجد أذكار في هذه الفئة.",
                       reply_to=reply_to, call=call)
        return

    progress = get_azkar_progress(uid, zikr_type)
    idx       = progress["zikr_index"]
    remaining = progress["remaining"]

    # إذا لم تبدأ الجلسة بعد أو انتهت — ابدأ من الأول
    if remaining == -1 or idx >= len(azkar):
        idx       = 0
        remaining = azkar[0]["repeat_count"]
        save_azkar_progress(uid, zikr_type, idx, remaining)

    _show_zikr(uid, cid, zikr_type, azkar, idx, remaining,
               reply_to=reply_to, call=call)


def _show_zikr(uid: int, cid: int, zikr_type: int,
               azkar: list, idx: int, remaining: int,
               reply_to: int = None, call=None) -> None:
    """يعرض الذكر الحالي مع أزرار التحكم."""
    total_azkar = len(azkar)
    zikr        = azkar[idx]
    icon, label = _LABELS[zikr_type]
    owner       = (uid, cid)

    # شريط التقدم الكلي (عدد الأذكار المكتملة)
    done_azkar = idx  # عدد الأذكار المكتملة حتى الآن
    bar        = _progress_bar(done_azkar, total_azkar)

    text = (
        f"{icon} <b>{label}</b>\n"
        f"{get_lines()}\n\n"
        f"{zikr['text']}\n\n"
        f"🔁 <b>{remaining}</b> مرة متبقية"
        + (f" من {zikr['repeat_count']}" if zikr["repeat_count"] > 1 else "")
        + f"\n\n{bar} ({done_azkar + 1}/{total_azkar})"
    )

    buttons = [
        btn("✅ التالي", "azkar_next",
            {"t": zikr_type, "i": idx, "r": remaining},
            owner=owner, color=_G),
        btn("🔁 إعادة البدء", "azkar_restart",
            {"t": zikr_type},
            owner=owner, color=_B),
        btn("❌ إغلاق", "azkar_close", {}, owner=owner, color=_R),
    ]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[1, 2])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[1, 2],
                owner_id=uid, reply_to=reply_to)


def _progress_bar(done: int, total: int, width: int = 8) -> str:
    filled = round(done / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def _reply_or_edit(cid, uid, text, reply_to=None, call=None):
    if call:
        try:
            bot.edit_message_text(text, cid, call.message.message_id,
                                  parse_mode="HTML")
        except Exception:
            pass
    else:
        bot.send_message(cid, text, parse_mode="HTML",
                         reply_to_message_id=reply_to)


# ══════════════════════════════════════════
# معالجات الأزرار
# ══════════════════════════════════════════

@register_action("azkar_next")
def on_next(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])
    idx       = int(data["i"])
    remaining = int(data["r"])

    azkar = get_azkar_list(zikr_type)
    if not azkar:
        bot.answer_callback_query(call.id, "❌ لا توجد أذكار.", show_alert=True)
        return

    # تحقق من أن البيانات لا تزال متزامنة مع قاعدة البيانات
    db_progress = get_azkar_progress(uid, zikr_type)
    if db_progress["zikr_index"] != idx or db_progress["remaining"] != remaining:
        # البيانات قديمة — استخدم قاعدة البيانات
        idx       = db_progress["zikr_index"]
        remaining = db_progress["remaining"]
        if remaining == -1:
            bot.answer_callback_query(call.id, "✅ انتهت الجلسة.", show_alert=True)
            return

    remaining -= 1

    if remaining > 0:
        # لا يزال هناك تكرارات لهذا الذكر
        save_azkar_progress(uid, zikr_type, idx, remaining)
        bot.answer_callback_query(call.id, f"✅ {remaining} مرة متبقية")
        _show_zikr(uid, cid, zikr_type, azkar, idx, remaining, call=call)

    else:
        # انتهى هذا الذكر — انتقل للتالي
        next_idx = idx + 1
        if next_idx < len(azkar):
            next_remaining = azkar[next_idx]["repeat_count"]
            save_azkar_progress(uid, zikr_type, next_idx, next_remaining)
            bot.answer_callback_query(call.id, "✅ الذكر التالي")
            _show_zikr(uid, cid, zikr_type, azkar, next_idx, next_remaining, call=call)
        else:
            # اكتملت جميع الأذكار
            reset_azkar_progress(uid, zikr_type)
            bot.answer_callback_query(call.id, "🎉 أتممت الأذكار!", show_alert=False)
            _show_completion(call, uid, cid, zikr_type)


@register_action("azkar_restart")
def on_restart(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])

    reset_azkar_progress(uid, zikr_type)
    bot.answer_callback_query(call.id, "🔁 تمت إعادة البدء")
    _start_session(uid, cid, zikr_type, call=call)


@register_action("azkar_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("azkar_start_again")
def on_start_again(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])

    reset_azkar_progress(uid, zikr_type)
    bot.answer_callback_query(call.id)
    _start_session(uid, cid, zikr_type, call=call)


# ══════════════════════════════════════════
# رسالة الإتمام
# ══════════════════════════════════════════

def _show_completion(call, uid: int, cid: int, zikr_type: int) -> None:
    icon, label = _LABELS[zikr_type]
    owner       = (uid, cid)
    text = (
        f"{icon} <b>{label}</b>\n"
        f"{get_lines()}\n\n"
        f"🎉 <b>أتممت {label} بنجاح!</b>\n\n"
        f"جزاك الله خيراً وتقبّل منك."
    )
    buttons = [
        btn("🔁 إعادة البدء", "azkar_start_again", {"t": zikr_type},
            owner=owner, color=_G),
        btn("❌ إغلاق", "azkar_close", {}, owner=owner, color=_R),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2])

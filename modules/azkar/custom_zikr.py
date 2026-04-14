"""
modules/azkar/custom_zikr.py
──────────────────────────────
ذكر مؤقت — يسمح للمستخدم بإنشاء ذكر شخصي مؤقت بدون قاعدة بيانات.

التدفق:
  1. المستخدم يرسل "ذكر"
  2. البوت يطلب نص الذكر
  3. البوت يطلب عدد التكرار (افتراضي 100، حد أقصى 1000)
  4. تبدأ الجلسة مع زر "✅ تسبيحة"
  5. كل ضغطة تنقص العداد وتُحدّث شريط التقدم
  6. عند الانتهاء: زر "🔁 كرر" أو "🗑 احذف"

ضمانات:
  - كل مستخدم له جلسة مستقلة
  - الأزرار تعمل فقط لصاحب الجلسة (owner)
  - الجلسة تنتهي تلقائياً بعد 30 دقيقة من آخر نشاط
  - العداد يُقرأ من الجلسة (لا من بيانات الزر) — يمنع الضغط المزدوج
  - لا حفظ في قاعدة البيانات
"""
import time
from core.bot import bot
from core.state_manager import StateManager
from utils.pagination import btn, send_ui, edit_ui, register_action

# ── ثوابت ──────────────────────────────────────────────────────────
_MAX_COUNT     = 1000
_DEFAULT_COUNT = 100
_SESSION_TTL   = 30 * 60   # 30 دقيقة بالثواني

# ── تخزين مؤقت: (user_id, chat_id) → {text, total, remaining, last_active} ──
_SESSIONS: dict[tuple, dict] = {}


# ══════════════════════════════════════════
# مساعدات الجلسة
# ══════════════════════════════════════════

def _get_session(uid: int, cid: int) -> dict | None:
    """يرجع الجلسة إذا كانت نشطة، أو None إذا انتهت."""
    key     = (uid, cid)
    session = _SESSIONS.get(key)
    if not session:
        return None
    if time.time() - session.get("last_active", 0) > _SESSION_TTL:
        _SESSIONS.pop(key, None)
        return None
    return session


def _touch(uid: int, cid: int) -> None:
    """يُحدّث وقت آخر نشاط للجلسة."""
    session = _SESSIONS.get((uid, cid))
    if session:
        session["last_active"] = time.time()


def _clear_session(uid: int, cid: int) -> None:
    _SESSIONS.pop((uid, cid), None)


# ══════════════════════════════════════════
# شريط التقدم المرئي
# ══════════════════════════════════════════

def _progress_bar(done: int, total: int, width: int = 10) -> str:
    """يبني شريط تقدم نصي. مثال: ████████░░ 8/10"""
    filled = round(done / total * width) if total else 0
    bar    = "█" * filled + "░" * (width - filled)
    return f"{bar} {done}/{total}"


# ══════════════════════════════════════════
# بناء رسالة الذكر
# ══════════════════════════════════════════

def _build_zikr_text(ztext: str, total: int, remaining: int) -> str:
    done = total - remaining
    pct  = round(done / total * 100) if total else 0
    bar  = _progress_bar(done, total)
    return (
        f"📿 <b>{ztext}</b>\n\n"
        f"{bar}\n"
        f"✅ <b>{done}</b> / {total} ({pct}%)"
    )


def _send_zikr_msg(cid: int, uid: int, ztext: str, total: int,
                   remaining: int, reply_to: int = None, call=None) -> None:
    owner   = (uid, cid)
    caption = _build_zikr_text(ztext, total, remaining)
    buttons = [
        btn("✅  تسبيحة", "czikr_tap", {}, owner=owner, color="su"),
        btn("❌ إلغاء",   "czikr_cancel", {}, owner=owner, color="d"),
    ]
    if call:
        edit_ui(call, text=caption, buttons=buttons, layout=[1, 1])
    else:
        send_ui(cid, text=caption, buttons=buttons, layout=[1, 1],
                owner_id=uid, reply_to=reply_to)


# ══════════════════════════════════════════
# نقطة الدخول — أمر "ذكر"
# ══════════════════════════════════════════

def handle_custom_zikr_command(message) -> bool:
    if (message.text or "").strip() != "ذكر":
        return False

    uid = message.from_user.id
    cid = message.chat.id

    # إذا كانت هناك جلسة نشطة — اسأل المستخدم
    if _get_session(uid, cid):
        _clear_session(uid, cid)

    StateManager.set(uid, cid, {"type": "czikr_awaiting_text"})
    bot.reply_to(
        message,
        "📿 <b>ذكر مؤقت</b>\n\nأرسل نص الذكر:\n\n"
        "<i>أرسل /cancel للإلغاء</i>",
        parse_mode="HTML"
    )
    return True


# ══════════════════════════════════════════
# معالج الإدخال النصي
# ══════════════════════════════════════════

def handle_custom_zikr_input(message) -> bool:
    uid   = message.from_user.id
    cid   = message.chat.id
    state = StateManager.get(uid, cid)
    if not state:
        return False

    s = state.get("type", "")

    # ── إلغاء ──
    if (message.text or "").strip() in ("/cancel", "إلغاء"):
        if s.startswith("czikr_"):
            StateManager.clear(uid, cid)
            bot.reply_to(message, "❌ تم الإلغاء.")
            return True
        return False

    # ── الخطوة 1: استقبال نص الذكر ──
    if s == "czikr_awaiting_text":
        text = (message.text or "").strip()
        if not text:
            bot.reply_to(message, "❌ أرسل نصاً صحيحاً.")
            return True
        if len(text) > 500:
            bot.reply_to(message, "❌ النص طويل جداً (الحد 500 حرف).")
            return True

        StateManager.clear(uid, cid)
        StateManager.set(uid, cid, {"type": "czikr_awaiting_count", "extra": {"text": text}})
        bot.reply_to(
            message,
            f"🔢 كم مرة تريد التسبيح؟\n\n"
            f"أرسل رقماً (1 – {_MAX_COUNT:,})\n"
            f"<i>أو أرسل أي شيء آخر للاستخدام الافتراضي ({_DEFAULT_COUNT})</i>",
            parse_mode="HTML"
        )
        return True

    # ── الخطوة 2: استقبال عدد التكرار ──
    if s == "czikr_awaiting_count":
        raw   = (message.text or "").strip()
        extra = state.get("extra") or {}
        ztext = extra.get("text", "")

        notice    = None
        raw_clean = raw.replace(",", "").replace("،", "")

        if not raw_clean.isdigit():
            total  = _DEFAULT_COUNT
            notice = f"⚠️ إدخال غير رقمي — تم استخدام العدد الافتراضي: <b>{_DEFAULT_COUNT}</b>"
        else:
            total = int(raw_clean)
            if total <= 0:
                total  = _DEFAULT_COUNT
                notice = f"⚠️ العدد يجب أن يكون أكبر من صفر — تم استخدام: <b>{_DEFAULT_COUNT}</b>"
            elif total > _MAX_COUNT:
                total  = _MAX_COUNT
                notice = f"⚠️ الحد الأقصى هو <b>{_MAX_COUNT:,}</b> — تم تقليص العدد تلقائياً."

        StateManager.clear(uid, cid)

        if notice:
            try:
                bot.reply_to(message, notice, parse_mode="HTML")
            except Exception:
                pass

        _SESSIONS[(uid, cid)] = {
            "text":        ztext,
            "total":       total,
            "remaining":   total,
            "last_active": time.time(),
        }
        _send_zikr_msg(cid, uid, ztext, total, total,
                       reply_to=message.message_id)
        return True

    return False


# ══════════════════════════════════════════
# معالجات الأزرار
# ══════════════════════════════════════════

@register_action("czikr_tap")
def on_tap(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id

    session = _get_session(uid, cid)
    if not session:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة. أرسل «ذكر» لبدء جديد.",
                                  show_alert=True)
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        return

    # قراءة العداد من الجلسة — يمنع الضغط المزدوج
    remaining = session["remaining"]
    total     = session["total"]
    ztext     = session["text"]

    if remaining <= 0:
        # الجلسة منتهية بالفعل — لا تفعل شيئاً
        bot.answer_callback_query(call.id)
        return

    remaining -= 1
    session["remaining"] = remaining
    _touch(uid, cid)

    if remaining > 0:
        done = total - remaining
        bot.answer_callback_query(call.id, f"✅ {done}/{total}")
        _send_zikr_msg(cid, uid, ztext, total, remaining, call=call)
    else:
        # اكتمل الذكر
        bot.answer_callback_query(call.id, "🎉 أتممت الذكر!", show_alert=False)
        owner   = (uid, cid)
        caption = (
            f"📿 <b>{ztext}</b>\n\n"
            f"{_progress_bar(total, total)}\n"
            f"🎉 <b>أتممت {total:,} مرة!</b>\n\n"
            f"ماذا تريد؟"
        )
        buttons = [
            btn("🔁 كرر",  "czikr_repeat", {}, owner=owner, color="su"),
            btn("🗑 احذف", "czikr_delete", {}, owner=owner, color="d"),
        ]
        edit_ui(call, text=caption, buttons=buttons, layout=[2])


@register_action("czikr_cancel")
def on_cancel(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id

    _clear_session(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء.")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


@register_action("czikr_repeat")
def on_repeat(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id

    session = _get_session(uid, cid)
    if not session:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة. أرسل «ذكر» لبدء جديد.",
                                  show_alert=True)
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        return

    total              = session["total"]
    session["remaining"] = total
    _touch(uid, cid)

    bot.answer_callback_query(call.id, "🔁 تمت إعادة التشغيل")
    _send_zikr_msg(cid, uid, session["text"], total, total, call=call)


@register_action("czikr_delete")
def on_delete(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id

    _clear_session(uid, cid)
    bot.answer_callback_query(call.id, "🗑 تم حذف الجلسة.")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass

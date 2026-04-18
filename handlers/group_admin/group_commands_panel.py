"""
handlers/group_admin/group_commands_panel.py
─────────────────────────────────────────────
لوحة "الأوامر" — إعدادات المجموعة للمشرفين

أقسام:
  🕐 التوقيت (tz_offset)
  📿 تذكيرات الأذكار (صباح / مساء / نوم / استيقاظ)
  ⏱ فترة إرسال الأذكار التلقائية (5-30 دقيقة)
  🔔 تفعيل / إيقاف الأذكار التلقائية (azkar_content)
"""
from core.bot import bot
from handlers.group_admin.permissions import is_admin, is_developer, can_pin_messages
from database.db_queries.groups_queries import (
    get_group_settings, update_group_setting, get_internal_group_id,
)
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines

_B = "p"
_G = "su"
_R = "d"

# ── أنواع الأذكار ──────────────────────────────────────────────────
_ZIKR_TYPES = {
    0: ("🌅", "الصباح",    "azkar_rem_morning"),
    1: ("🌙", "المساء",    "azkar_rem_evening"),
    2: ("😴", "النوم",     "azkar_rem_sleep"),
    3: ("☀️", "الاستيقاظ", "azkar_rem_wakeup"),
}

# ── فترات الإرسال المسموحة (دقائق) ────────────────────────────────
_INTERVALS = [5, 10, 15, 20, 25, 30]

# ── ساعات التذكير المتاحة (0-23) ───────────────────────────────────
_HOURS = list(range(0, 24))


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def open_commands_panel(message) -> bool:
    """يفتح لوحة الأوامر — للمشرفين فقط في المجموعات."""
    if message.chat.type not in ("group", "supergroup"):
        return False

    text = (message.text or "").strip()
    if text not in ("الأوامر", "/commands"):
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if not is_admin(message) or not is_developer(message):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
        return True

    # تأكد من تسجيل المجموعة
    if not get_internal_group_id(cid):
        from database.db_queries.groups_queries import upsert_group
        upsert_group(cid, message.chat.title or "Unknown")

    _send_main_panel(message)
    return True


def _send_main_panel(message):
    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)
    s     = get_group_settings(cid)

    tz_label      = _fmt_tz(s["tz_offset"])
    azkar_label   = "✅ مفعّل" if s["azkar_enabled"] else "❌ موقوف"
    interval_label = f"{s['azkar_interval']} دقيقة"

    text = (
        f"⚙️ <b>إعدادات المجموعة</b>\n{get_lines()}\n\n"
        f"🕐 التوقيت: <b>{tz_label}</b>\n"
        f"🔔 الأذكار التلقائية: <b>{azkar_label}</b>\n"
        f"⏱ فترة الإرسال: <b>{interval_label}</b>\n\n"
        f"📿 <b>تذكيرات الأذكار:</b>\n"
        + _reminders_summary(s)
    )

    buttons = [
        btn("🕐 تعديل التوقيت",          "grp_tz_panel",       {}, owner=owner, color=_B),
        btn("📿 تذكيرات الأذكار",         "grp_rem_panel",      {}, owner=owner, color=_B),
        btn("⏱ وقت إرسال الأذكار",       "grp_interval_panel", {}, owner=owner, color=_B),
        btn(f"🔔 الأذكار التلقائية: {azkar_label}",
            "grp_toggle_azkar", {}, owner=owner,
            color=_G if s["azkar_enabled"] else _R),
        btn("❌ إغلاق", "grp_close", {}, owner=owner, color=_R),
    ]
    send_ui(cid, text=text, buttons=buttons, layout=[2, 1, 1, 1],
            owner_id=uid, reply_to=message.message_id)


def _reminders_summary(s: dict) -> str:
    lines = []
    for zikr_type, (icon, label, col) in _ZIKR_TYPES.items():
        hour = s.get(col)
        val  = f"{hour:02d}:00" if hour is not None else "—"
        lines.append(f"  {icon} {label}: <b>{val}</b>")
    return "\n".join(lines)


def _fmt_tz(offset_minutes: int) -> str:
    sign  = "+" if offset_minutes >= 0 else "-"
    hours = abs(offset_minutes) // 60
    mins  = abs(offset_minutes) % 60
    return f"UTC{sign}{hours}" if mins == 0 else f"UTC{sign}{hours}:{mins:02d}"


# ══════════════════════════════════════════
# 🕐 التوقيت
# ══════════════════════════════════════════

@register_action("grp_tz_panel")
def on_tz_panel(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)

    if not _check_admin(call):
        return

    s          = get_group_settings(cid)
    current_tz = s["tz_offset"]

    # عرض أزرار UTC-12 → UTC+14 بخطوة ساعة
    offsets = list(range(-12 * 60, 15 * 60, 60))  # -720 → +840
    buttons = []
    for off in offsets:
        label = _fmt_tz(off)
        color = _G if off == current_tz else _B
        buttons.append(btn(label, "grp_set_tz", {"tz": off}, owner=owner, color=color))

    buttons.append(btn("🔙 رجوع", "grp_main_back", {}, owner=owner, color=_R))

    # 4 أزرار في كل صف
    n = len(buttons) - 1
    layout = [4] * (n // 4) + ([n % 4] if n % 4 else []) + [1]

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"🕐 <b>اختر التوقيت</b>\n{get_lines()}\n\nالحالي: <b>{_fmt_tz(current_tz)}</b>",
            buttons=buttons, layout=layout)


@register_action("grp_set_tz")
def on_set_tz(call, data):
    if not _check_admin(call):
        return
    cid = call.message.chat.id
    tz  = int(data["tz"])
    update_group_setting(cid, "tz_offset", tz)
    bot.answer_callback_query(call.id, f"✅ تم ضبط التوقيت: {_fmt_tz(tz)}", show_alert=True)
    on_tz_panel(call, {})


# ══════════════════════════════════════════
# 📿 تذكيرات الأذكار
# ══════════════════════════════════════════

@register_action("grp_rem_panel")
def on_rem_panel(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)

    if not _check_admin(call):
        return

    s = get_group_settings(cid)
    bot.answer_callback_query(call.id)

    text = f"📿 <b>تذكيرات الأذكار</b>\n{get_lines()}\n\nاختر الفئة لضبط وقت التذكير:"
    buttons = []
    for zikr_type, (icon, label, col) in _ZIKR_TYPES.items():
        hour = s.get(col)
        from utils.helpers import format_hour_arabic
        val = format_hour_arabic(hour) if hour is not None else "—"

        buttons.append(btn(
            f"{icon} {label} ({val})",
            "grp_rem_type", {"type": zikr_type},
            owner=owner, color=_B
        ))
    buttons.append(btn("🔙 رجوع", "grp_main_back", {}, owner=owner, color=_R))
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1, 1, 1])


@register_action("grp_rem_type")
def on_rem_type(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    owner     = (uid, cid)
    zikr_type = int(data["type"])

    if not _check_admin(call):
        return

    icon, label, col = _ZIKR_TYPES[zikr_type]
    s    = get_group_settings(cid)
    cur  = s.get(col)

    from utils.helpers import format_hour_arabic

    text = (
        f"{icon} <b>{label}</b>\n{get_lines()}\n\n"
        f"الوقت الحالي: <b>{format_hour_arabic(cur) if cur is not None else '—'}</b>\n\n"
        f"اختر الساعة (بتوقيت المجموعة):"
    )

    buttons = []
    for h in _HOURS:
        color = _G if h == cur else _B
        buttons.append(btn(
            f"{format_hour_arabic(h)}",
            "grp_set_rem",
            {"type": zikr_type, "hour": h},
            owner=owner, color=color
        ))
    # زر إلغاء التذكير
    buttons.append(btn("🚫 إلغاء التذكير", "grp_clear_rem",
                       {"type": zikr_type}, owner=owner, color=_R))
    buttons.append(btn("🔙 رجوع", "grp_rem_panel", {}, owner=owner, color=_R))

    # 4 ساعات في كل صف
    n = len(_HOURS)
    layout = [3] * (n // 3) + ([n % 3] if n % 3 else []) + [1, 1]

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("grp_set_rem")
def on_set_rem(call, data):
    if not _check_admin(call):
        return

    cid       = call.message.chat.id
    zikr_type = int(data["type"])
    hour      = int(data["hour"])
    icon, label, col = _ZIKR_TYPES[zikr_type]

    update_group_setting(cid, col, hour)

    # إشعار بصلاحية التثبيت
    pin_note = ""
    if not can_pin_messages(cid):
        pin_note = "\n\n⚠️ البوت لا يملك صلاحية تثبيت الرسائل. امنحه إياها لتثبيت رسائل التذكير."

    bot.answer_callback_query(
        call.id,
        f"✅ تم ضبط تذكير {label} على {hour:02d}:00",
        show_alert=True
    )

    if pin_note:
        try:
            bot.send_message(cid, f"⚠️ البوت لا يملك صلاحية تثبيت الرسائل.\n"
                                  f"امنحه صلاحية <b>تثبيت الرسائل</b> لتثبيت تذكيرات الأذكار تلقائياً.",
                             parse_mode="HTML")
        except Exception:
            pass

    on_rem_type(call, {"type": zikr_type})


@register_action("grp_clear_rem")
def on_clear_rem(call, data):
    if not _check_admin(call):
        return

    cid       = call.message.chat.id
    zikr_type = int(data["type"])
    icon, label, col = _ZIKR_TYPES[zikr_type]

    update_group_setting(cid, col, None)
    bot.answer_callback_query(call.id, f"✅ تم إلغاء تذكير {label}", show_alert=True)
    on_rem_type(call, {"type": zikr_type})


# ══════════════════════════════════════════
# ⏱ فترة إرسال الأذكار التلقائية
# ══════════════════════════════════════════

@register_action("grp_interval_panel")
def on_interval_panel(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)

    if not _check_admin(call):
        return

    s       = get_group_settings(cid)
    current = s["azkar_interval"]

    text = (
        f"⏱ <b>فترة إرسال الأذكار التلقائية</b>\n{get_lines()}\n\n"
        f"الحالية: <b>{current} دقيقة</b>\n\n"
        f"اختر الفترة:"
    )
    buttons = [
        btn(
            f"{'✅ ' if v == current else ''}{v} دقيقة",
            "grp_set_interval", {"val": v},
            owner=owner,
            color=_G if v == current else _B
        )
        for v in _INTERVALS
    ]
    buttons.append(btn("🔙 رجوع", "grp_main_back", {}, owner=owner, color=_R))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[3, 3, 1])


@register_action("grp_set_interval")
def on_set_interval(call, data):
    if not _check_admin(call):
        return

    cid = call.message.chat.id
    val = int(data["val"])

    if val not in _INTERVALS:
        bot.answer_callback_query(call.id, "❌ قيمة غير صالحة.", show_alert=True)
        return

    update_group_setting(cid, "azkar_interval", val)
    # تحديث الـ throttle في azkar_sender
    try:
        from modules.content_hub.azkar_sender import _last_sent
        _last_sent.pop(cid, None)
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"✅ تم ضبط الفترة: {val} دقيقة", show_alert=True)
    on_interval_panel(call, {})


# ══════════════════════════════════════════
# 🔔 تفعيل / إيقاف الأذكار التلقائية
# ══════════════════════════════════════════

@register_action("grp_toggle_azkar")
def on_toggle_azkar(call, data):
    if not _check_admin(call):
        return

    cid     = call.message.chat.id
    s       = get_group_settings(cid)
    enabled = not bool(s["azkar_enabled"])

    update_group_setting(cid, "azkar_enabled", 1 if enabled else 0)

    if not enabled:
        from modules.content_hub.azkar_sender import _last_sent
        _last_sent.pop(cid, None)

    label = "✅ مفعّل" if enabled else "❌ موقوف"
    bot.answer_callback_query(call.id, f"الأذكار التلقائية: {label}", show_alert=True)
    on_main_back(call, {})


# ══════════════════════════════════════════
# 🔙 رجوع / إغلاق
# ══════════════════════════════════════════

@register_action("grp_main_back")
def on_main_back(call, data):
    if not _check_admin(call):
        return

    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    s     = get_group_settings(cid)

    tz_label      = _fmt_tz(s["tz_offset"])
    azkar_label   = "✅ مفعّل" if s["azkar_enabled"] else "❌ موقوف"
    interval_label = f"{s['azkar_interval']} دقيقة"

    text = (
        f"⚙️ <b>إعدادات المجموعة</b>\n{get_lines()}\n\n"
        f"🕐 التوقيت: <b>{tz_label}</b>\n"
        f"🔔 الأذكار التلقائية: <b>{azkar_label}</b>\n"
        f"⏱ فترة الإرسال: <b>{interval_label}</b>\n\n"
        f"📿 <b>تذكيرات الأذكار:</b>\n"
        + _reminders_summary(s)
    )

    buttons = [
        btn("🕐 تعديل التوقيت",          "grp_tz_panel",       {}, owner=owner, color=_B),
        btn("📿 تذكيرات الأذكار",         "grp_rem_panel",      {}, owner=owner, color=_B),
        btn("⏱ وقت إرسال الأذكار",       "grp_interval_panel", {}, owner=owner, color=_B),
        btn(f"🔔 الأذكار التلقائية: {azkar_label}",
            "grp_toggle_azkar", {}, owner=owner,
            color=_G if s["azkar_enabled"] else _R),
        btn("❌ إغلاق", "grp_close", {}, owner=owner, color=_R),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1, 1, 1])


@register_action("grp_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# مساعد: التحقق من صلاحية المشرف
# ══════════════════════════════════════════

def _check_admin(call) -> bool:
    """يتحقق من أن مُرسِل الـ callback مشرف. يرد بخطأ إذا لم يكن كذلك."""
    try:
        member = bot.get_chat_member(call.message.chat.id, call.from_user.id)
        if member.status in ("administrator", "creator"):
            return True
    except Exception:
        pass
    bot.answer_callback_query(call.id, "❌ هذا الإجراء للمشرفين فقط.", show_alert=True)
    return False

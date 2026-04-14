"""
modules/azkar/azkar_reminder.py
─────────────────────────────────
يُرسَل من المُجدوِل كل 5 دقائق.
يتحقق من تذكيرات الأذكار المجدولة للمجموعات ويرسل رسالة تفاعلية.

زر "عرض الذكر" في الرسالة:
  - يفتح محادثة خاصة مع البوت
  - يرسل للمستخدم جلسة الأذكار المناسبة
"""
from core.bot import bot
from database.db_queries.groups_queries import get_groups_with_reminder
from utils.pagination import btn, register_action, edit_ui, send_ui
from utils.pagination.buttons import build_keyboard
from utils.helpers import get_lines
from database.db_queries.azkar_queries import (
    add_azkar_reminder, delete_azkar_reminder,
    get_user_azkar_reminders, count_user_azkar_reminders,
)

# أنواع الأذكار: (عمود_التذكير, zikr_type, اسم_عربي, أمر_المستخدم)
_REMINDER_TYPES = [
    ("azkar_rem_morning", 0, "أذكار الصباح",    "أذكار الصباح"),
    ("azkar_rem_evening", 1, "أذكار المساء",    "أذكار المساء"),
    ("azkar_rem_sleep",   2, "أذكار النوم",     "أذكار النوم"),
    ("azkar_rem_wakeup",  3, "أذكار الاستيقاظ", "أذكار الاستيقاظ"),
]

_ICONS = {0: "🌅", 1: "🌙", 2: "😴", 3: "☀️"}


def fire_group_azkar_reminders(utc_hour: int, utc_minute: int) -> None:
    """
    يُشغَّل كل 5 دقائق من المُجدوِل.
    يرسل تذكيرات الأذكار للمجموعات التي حان وقتها.
    """
    # نتحقق فقط عند الدقيقة 0 من كل ساعة (التذكيرات مضبوطة على ساعات كاملة)
    if utc_minute != 0:
        return

    for col, zikr_type, label, command in _REMINDER_TYPES:
        try:
            _fire_type(col, zikr_type, label, command, utc_hour)
        except Exception as e:
            print(f"[AzkarReminder] خطأ في {col}: {e}")


def _fire_type(col: str, zikr_type: int, label: str, command: str,
               utc_hour: int) -> None:
    """يرسل تذكير نوع أذكار واحد لجميع المجموعات المستحقة."""
    groups = get_groups_with_reminder(col)
    for g in groups:
        tg_group_id = g["group_id"]
        tz_offset   = g.get("tz_offset") or 180   # افتراضي +3 (اليمن)
        local_hour  = (utc_hour + tz_offset // 60) % 24

        if local_hour != g["hour"]:
            continue

        _send_reminder_message(tg_group_id, zikr_type, label, command)


def _send_reminder_message(tg_group_id: int, zikr_type: int,
                            label: str, command: str) -> None:
    """يرسل رسالة التذكير في المجموعة مع زر تفاعلي، ويثبّتها إن أمكن."""
    icon = _ICONS.get(zikr_type, "📿")
    text = (
        f"{icon} <b>حان وقت {label}</b>\n\n"
        f"اضغط الزر أدناه لعرض الأذكار في محادثتك الخاصة مع البوت."
    )

    # الزر يفتح محادثة خاصة مع البوت ويرسل الأمر تلقائياً
    try:
        bot_info  = bot.get_me()
        bot_uname = bot_info.username or ""
        start_param = f"azkar_{zikr_type}"
        url = f"https://t.me/{bot_uname}?start={start_param}"
    except Exception:
        url = None

    if url:
        from utils.keyboards import ui_btn, build_keyboard as _bk
        markup = _bk([ui_btn(f"{icon} عرض {label}", url=url)], [1])
    else:
        markup = None

    try:
        sent = bot.send_message(
            tg_group_id, text,
            parse_mode="HTML",
            reply_markup=markup,
        )
        # محاولة تثبيت الرسالة
        try:
            bot.pin_chat_message(tg_group_id, sent.message_id,
                                 disable_notification=True)
        except Exception:
            pass  # البوت لا يملك صلاحية التثبيت — تجاهل صامت
    except Exception as e:
        print(f"[AzkarReminder] فشل الإرسال للمجموعة {tg_group_id}: {e}")


def _fire_reminder(reminder: dict) -> None:
    """
    واجهة متوافقة مع daily_tasks.py (تذكيرات المستخدمين الفردية).
    reminder: صف من azkar_reminders مع user_id, azkar_type, ...
    """
    from database.db_queries.azkar_queries import get_azkar_list
    user_id    = reminder.get("user_id")
    azkar_type = reminder.get("azkar_type", 0)

    label   = {0: "أذكار الصباح", 1: "أذكار المساء",
               2: "أذكار النوم",  3: "أذكار الاستيقاظ"}.get(azkar_type, "الأذكار")
    icon    = _ICONS.get(azkar_type, "📿")

    try:
        bot_info  = bot.get_me()
        bot_uname = bot_info.username or ""
        url = f"https://t.me/{bot_uname}?start=azkar_{azkar_type}"
        from utils.keyboards import ui_btn, build_keyboard as _bk
        markup = _bk([ui_btn(f"{icon} ابدأ {label}", url=url)], [1])
    except Exception:
        markup = None

    try:
        bot.send_message(
            user_id,
            f"{icon} <b>تذكير: {label}</b>\n\nاضغط الزر لبدء الأذكار.",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"[AzkarReminder] فشل إرسال تذكير للمستخدم {user_id}: {e}")


# ══════════════════════════════════════════
# أمر "ذكّرني ذكري" — تذكيرات الأذكار الشخصية
# ══════════════════════════════════════════

_REMINDER_COMMANDS = {
    "ذكّرني ذكري":       None,   # يفتح قائمة الاختيار
    "ذكرني ذكري":        None,
    "تذكيرات الأذكار":   None,
}

_TYPE_LABELS = {
    0: ("🌅", "أذكار الصباح"),
    1: ("🌙", "أذكار المساء"),
    2: ("😴", "أذكار النوم"),
    3: ("☀️", "أذكار الاستيقاظ"),
}

_MAX_REMINDERS = 3   # حد أقصى لعدد التذكيرات لكل مستخدم


def handle_reminder_command(message) -> bool:
    """
    يعالج أمر تذكيرات الأذكار الشخصية.
    يرجع True إذا تم التعامل مع الأمر.
    """
    text = (message.text or "").strip()
    if text not in _REMINDER_COMMANDS:
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    reminders = get_user_azkar_reminders(uid)
    count     = len(reminders)

    text_msg = f"🔔 <b>تذكيرات الأذكار</b>\n{get_lines()}\n\n"
    if reminders:
        text_msg += "تذكيراتك الحالية:\n"
        for r in reminders:
            icon, label = _TYPE_LABELS.get(r["azkar_type"], ("📿", "أذكار"))
            text_msg += f"  {icon} {label} — {r['hour']:02d}:{r['minute']:02d}\n"
        text_msg += "\n"
    else:
        text_msg += "لا توجد تذكيرات مضافة بعد.\n\n"

    text_msg += f"الحد الأقصى: {_MAX_REMINDERS} تذكيرات"

    buttons = []
    if count < _MAX_REMINDERS:
        buttons.append(btn("➕ إضافة تذكير", "azkar_rem_add_type",
                           {}, owner=owner, color="su"))
    if reminders:
        buttons.append(btn("🗑 حذف تذكير", "azkar_rem_delete_list",
                           {}, owner=owner, color="d"))
    buttons.append(btn("❌ إغلاق", "azkar_rem_close", {}, owner=owner, color="d"))

    send_ui(cid, text=text_msg, buttons=buttons,
            layout=[1] * len(buttons), owner_id=uid,
            reply_to=message.message_id)
    return True


# ══════════════════════════════════════════
# Reminder list helper
# ══════════════════════════════════════════

def _show_reminder_list(call, uid: int, cid: int, owner: tuple, reminders: list) -> None:
    count    = len(reminders)
    text_msg = f"🔔 <b>تذكيرات الأذكار</b>\n{get_lines()}\n\n"
    if reminders:
        for r in reminders:
            icon, label = _TYPE_LABELS.get(r["azkar_type"], ("📿", "أذكار"))
            text_msg += f"  {icon} {label} — {r['hour']:02d}:{r['minute']:02d}\n"
        text_msg += "\n"
    else:
        text_msg += "لا توجد تذكيرات.\n\n"
    text_msg += f"الحد الأقصى: {_MAX_REMINDERS} تذكيرات"

    buttons = []
    if count < _MAX_REMINDERS:
        buttons.append(btn("➕ إضافة تذكير", "azkar_rem_add_type",
                           {}, owner=owner, color="su"))
    if reminders:
        buttons.append(btn("🗑 حذف تذكير", "azkar_rem_delete_list",
                           {}, owner=owner, color="d"))
    buttons.append(btn("❌ إغلاق", "azkar_rem_close", {}, owner=owner, color="d"))
    edit_ui(call, text=text_msg, buttons=buttons, layout=[1] * len(buttons))


# ══════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════

@register_action("azkar_rem_add_type")
def on_add_type(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    buttons = [
        btn(f"{icon} {label}", "azkar_rem_add_hour",
            {"t": t}, owner=owner, color="p")
        for t, (icon, label) in _TYPE_LABELS.items()
    ]
    buttons.append(btn("🔙 رجوع", "azkar_rem_back", {}, owner=owner, color="d"))
    edit_ui(call, text="📿 <b>اختر نوع الأذكار للتذكير:</b>",
            buttons=buttons, layout=[1, 1, 1, 1, 1])


@register_action("azkar_rem_add_hour")
def on_add_hour(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    owner     = (uid, cid)
    zikr_type = int(data["t"])
    icon, label = _TYPE_LABELS[zikr_type]
    bot.answer_callback_query(call.id)

    buttons = [
        btn(f"{h:02d}:00", "azkar_rem_save",
            {"t": zikr_type, "h": h, "m": 0},
            owner=owner, color="p")
        for h in range(24)
    ]
    buttons.append(btn("🔙 رجوع", "azkar_rem_add_type", {}, owner=owner, color="d"))
    edit_ui(call,
            text=f"{icon} <b>{label}</b>\n\nاختر الساعة (بتوقيتك المحلي):",
            buttons=buttons, layout=[4] * 6 + [1])


@register_action("azkar_rem_save")
def on_save(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    owner     = (uid, cid)
    zikr_type = int(data["t"])
    hour      = int(data["h"])
    minute    = int(data.get("m", 0))

    count = count_user_azkar_reminders(uid)
    if count >= _MAX_REMINDERS:
        bot.answer_callback_query(
            call.id,
            f"❌ وصلت للحد الأقصى ({_MAX_REMINDERS} تذكيرات).",
            show_alert=True
        )
        return

    add_azkar_reminder(uid, zikr_type, hour, minute)
    icon, label = _TYPE_LABELS[zikr_type]
    bot.answer_callback_query(
        call.id,
        f"✅ تم إضافة تذكير {label} على {hour:02d}:{minute:02d}",
        show_alert=True
    )
    reminders = get_user_azkar_reminders(uid)
    _show_reminder_list(call, uid, cid, owner, reminders)


@register_action("azkar_rem_delete_list")
def on_delete_list(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    reminders = get_user_azkar_reminders(uid)
    if not reminders:
        bot.answer_callback_query(call.id, "لا توجد تذكيرات.", show_alert=True)
        return

    buttons = [
        btn(
            f"🗑 {_TYPE_LABELS.get(r['azkar_type'], ('📿', 'أذكار'))[0]} "
            f"{_TYPE_LABELS.get(r['azkar_type'], ('📿', 'أذكار'))[1]} "
            f"{r['hour']:02d}:{r['minute']:02d}",
            "azkar_rem_delete_one", {"rid": r["id"]},
            owner=owner, color="d"
        )
        for r in reminders
    ]
    buttons.append(btn("🔙 رجوع", "azkar_rem_back", {}, owner=owner, color="p"))
    edit_ui(call, text="🗑 <b>اختر التذكير للحذف:</b>",
            buttons=buttons, layout=[1] * len(buttons))


@register_action("azkar_rem_delete_one")
def on_delete_one(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    rid   = int(data["rid"])

    delete_azkar_reminder(rid, uid)
    bot.answer_callback_query(call.id, "✅ تم حذف التذكير.", show_alert=True)
    reminders = get_user_azkar_reminders(uid)
    _show_reminder_list(call, uid, cid, owner, reminders)


@register_action("azkar_rem_back")
def on_back(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    reminders = get_user_azkar_reminders(uid)
    _show_reminder_list(call, uid, cid, owner, reminders)


@register_action("azkar_rem_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

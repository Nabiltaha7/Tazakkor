"""
modules/azkar/azkar_reminder.py
─────────────────────────────────
Group azkar reminders — fires from the scheduler every 5 minutes.

System B: Fixed-time azkar reminders per group.
  Each group stores a local hour (0–23) for each azkar type:
    azkar_rem_morning  → 🌅 أذكار الصباح
    azkar_rem_evening  → 🌙 أذكار المساء
    azkar_rem_sleep    → 😴 أذكار النوم
    azkar_rem_wakeup   → ☀️ أذكار الاستيقاظ

  The scheduler calls fire_group_azkar_reminders(utc_hour, utc_minute)
  every 5 minutes. For each group, the stored local hour is converted
  to UTC using the group's tz_offset (stored in minutes, e.g. 180 = UTC+3).
  A reminder fires when UTC hour matches and has not been sent yet this hour.

Duplicate prevention:
  _sent_log: dict[(group_id, col, date_hour_str)] → True
  Cleared automatically — keys include the date+hour so they expire naturally.
"""
from core.bot import bot
from database.db_queries.groups_queries import get_groups_with_reminder
from utils.pagination import btn, register_action, edit_ui, send_ui
from utils.helpers import get_lines
from database.db_queries.azkar_queries import (
    add_azkar_reminder, delete_azkar_reminder,
    get_user_azkar_reminders, count_user_azkar_reminders,
)

# ── Azkar types: (db_column, zikr_type, arabic_label, user_command) ──────────
_REMINDER_TYPES = [
    ("azkar_rem_morning", 0, "أذكار الصباح",    "أذكار الصباح"),
    ("azkar_rem_evening", 1, "أذكار المساء",    "أذكار المساء"),
    ("azkar_rem_sleep",   2, "أذكار النوم",     "أذكار النوم"),
    ("azkar_rem_wakeup",  3, "أذكار الاستيقاظ", "أذكار الاستيقاظ"),
]

_ICONS = {0: "🌅", 1: "🌙", 2: "😴", 3: "☀️"}

# ── Sent-log: prevents duplicate sends within the same UTC hour ───────────────
# Key: (group_id, col, "YYYY-MM-DD HH") — expires naturally as the hour changes
_sent_log: dict[tuple, bool] = {}


def _sent_key(group_id: int, col: str, utc_hour: int) -> tuple:
    """Generates a dedup key scoped to the current UTC date+hour."""
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (group_id, col, f"{date_str} {utc_hour:02d}")


def _prune_sent_log(utc_hour: int) -> None:
    """Removes stale entries from _sent_log (older than current hour)."""
    from datetime import datetime, timezone
    current_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d") + f" {utc_hour:02d}"
    stale = [k for k in _sent_log if not str(k[2]).startswith(current_prefix[:13])]
    for k in stale:
        del _sent_log[k]


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point — called by scheduler every 5 minutes
# ══════════════════════════════════════════════════════════════════════════════

def fire_group_azkar_reminders(utc_hour: int, utc_minute: int) -> None:
    """
    Called every 5 minutes by the scheduler.
    Sends azkar reminders to groups whose configured local hour matches now.

    NOTE: We do NOT gate on utc_minute == 0.
    The scheduler fires every 5 min (at :00, :05, :10 ... or offset variants).
    Duplicate prevention is handled by _sent_log keyed on (group, col, date+hour).
    This guarantees delivery within the first 5-minute window of the target hour.
    """
    _prune_sent_log(utc_hour)

    for col, zikr_type, label, command in _REMINDER_TYPES:
        try:
            _fire_type(col, zikr_type, label, command, utc_hour, utc_minute)
        except Exception as e:
            import traceback
            print(f"[AZKAR_CHECK] ❌ Error processing {col}: {e}")
            traceback.print_exc()


def _fire_type(col: str, zikr_type: int, label: str, command: str,
               utc_hour: int, utc_minute: int) -> None:
    """Checks all groups for a single azkar type and sends if due."""
    groups = get_groups_with_reminder(col)

    if not groups:
        return

    for g in groups:
        group_id   = g["group_id"]
        # tz_offset is stored in MINUTES (e.g. 180 = UTC+3, 330 = UTC+5:30)
        tz_minutes = g.get("tz_offset") or 180
        target_local_hour = g["hour"]   # the hour admin configured (local time)

        # Convert current UTC time to group's local time
        utc_total_minutes   = utc_hour * 60 + utc_minute
        local_total_minutes = (utc_total_minutes + tz_minutes) % (24 * 60)
        local_hour          = local_total_minutes // 60

        print(
            f"[AZKAR_CHECK] group={group_id} col={col} "
            f"utc={utc_hour:02d}:{utc_minute:02d} "
            f"tz_offset={tz_minutes}min "
            f"local={local_hour:02d}:xx "
            f"target={target_local_hour:02d}:00"
        )

        if local_hour != target_local_hour:
            print(f"[AZKAR_SKIPPED] group={group_id} col={col} — "
                  f"local hour {local_hour} ≠ target {target_local_hour}")
            continue

        # Dedup: only send once per UTC hour per group per type
        key = _sent_key(group_id, col, utc_hour)
        if key in _sent_log:
            print(f"[AZKAR_SKIPPED] group={group_id} col={col} — "
                  f"already sent this hour (key={key})")
            continue

        print(f"[AZKAR_MATCH] group={group_id} col={col} "
              f"local={local_hour:02d}:00 — sending {label}")

        _sent_log[key] = True
        _send_reminder_message(group_id, zikr_type, label, command)


# ══════════════════════════════════════════════════════════════════════════════
# Message sender
# ══════════════════════════════════════════════════════════════════════════════

def _send_reminder_message(tg_group_id: int, zikr_type: int,
                            label: str, command: str) -> None:
    """Sends the azkar reminder message to a group with a deep-link button."""
    icon = _ICONS.get(zikr_type, "📿")
    text = (
        f"{icon} <b>حان وقت {label}</b>\n\n"
        f"اضغط الزر أدناه لعرض الأذكار في محادثتك الخاصة مع البوت."
    )

    markup = None
    try:
        bot_info    = bot.get_me()
        bot_uname   = bot_info.username or ""
        start_param = f"azkar_{zikr_type}"
        url         = f"https://t.me/{bot_uname}?start={start_param}"
        from utils.keyboards import ui_btn, build_keyboard as _bk
        markup = _bk([ui_btn(f"{icon} عرض {label}", url=url)], [1])
    except Exception as e:
        print(f"[AZKAR_SENT] ⚠️ Could not build button for group {tg_group_id}: {e}")

    try:
        sent = bot.send_message(
            tg_group_id, text,
            parse_mode="HTML",
            reply_markup=markup,
        )
        print(f"[AZKAR_SENT] ✅ group={tg_group_id} type={zikr_type} ({label})")

        # Attempt to pin — silent fail if no permission
        try:
            bot.pin_chat_message(tg_group_id, sent.message_id,
                                 disable_notification=True)
        except Exception:
            pass

    except Exception as e:
        print(f"[AZKAR_SENT] ❌ group={tg_group_id} type={zikr_type} — {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Personal user reminders (System A — individual users, not groups)
# ══════════════════════════════════════════════════════════════════════════════

def _fire_reminder(reminder: dict) -> None:
    """
    Fires a personal azkar reminder for a single user.
    Called by daily_tasks.fire_azkar_reminders() from the scheduler.
    reminder: row from azkar_reminders with user_id, azkar_type, hour, minute, tz_offset
    """
    user_id    = reminder.get("user_id")
    azkar_type = reminder.get("azkar_type", 0)

    label = {
        0: "أذكار الصباح",
        1: "أذكار المساء",
        2: "أذكار النوم",
        3: "أذكار الاستيقاظ",
    }.get(azkar_type, "الأذكار")
    icon = _ICONS.get(azkar_type, "📿")

    markup = None
    try:
        bot_info  = bot.get_me()
        bot_uname = bot_info.username or ""
        url       = f"https://t.me/{bot_uname}?start=azkar_{azkar_type}"
        from utils.keyboards import ui_btn, build_keyboard as _bk
        markup = _bk([ui_btn(f"{icon} ابدأ {label}", url=url)], [1])
    except Exception:
        pass

    try:
        bot.send_message(
            user_id,
            f"{icon} <b>تذكير: {label}</b>\n\nاضغط الزر لبدء الأذكار.",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"[AZKAR_SENT] ❌ personal reminder user={user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Personal reminder UI — "ذكّرني ذكري" command
# ══════════════════════════════════════════════════════════════════════════════

_REMINDER_COMMANDS = {
    "ذكّرني ذكري",
    "ذكرني ذكري",
    "تذكيرات الأذكار",
}

_TYPE_LABELS = {
    0: ("🌅", "أذكار الصباح"),
    1: ("🌙", "أذكار المساء"),
    2: ("😴", "أذكار النوم"),
    3: ("☀️", "أذكار الاستيقاظ"),
}

_MAX_REMINDERS = 3


def handle_reminder_command(message) -> bool:
    """Handles the personal azkar reminder command. Returns True if handled."""
    text = (message.text or "").strip()
    if text not in _REMINDER_COMMANDS:
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    reminders = get_user_azkar_reminders(uid)
    count     = len(reminders)

    from utils.helpers import format_hour_arabic
    text_msg = f"🔔 <b>تذكيرات الأذكار</b>\n{get_lines()}\n\n"
    if reminders:
        text_msg += "تذكيراتك الحالية:\n"
        for r in reminders:
            icon, label = _TYPE_LABELS.get(r["azkar_type"], ("📿", "أذكار"))
            time_label  = format_hour_arabic(r["hour"], r["minute"])
            text_msg += f"  {icon} {label} — {time_label}\n"
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


# ══════════════════════════════════════════════════════════════════════════════
# Reminder list helper (shared by multiple callbacks)
# ══════════════════════════════════════════════════════════════════════════════

def _show_reminder_list(call, uid: int, cid: int, owner: tuple,
                        reminders: list) -> None:
    from utils.helpers import format_hour_arabic
    count    = len(reminders)
    text_msg = f"🔔 <b>تذكيرات الأذكار</b>\n{get_lines()}\n\n"
    if reminders:
        for r in reminders:
            icon, label = _TYPE_LABELS.get(r["azkar_type"], ("📿", "أذكار"))
            time_label  = format_hour_arabic(r["hour"], r["minute"])
            text_msg += f"  {icon} {label} — {time_label}\n"
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


# ══════════════════════════════════════════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════════════════════════════════════════

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
    uid         = call.from_user.id
    cid         = call.message.chat.id
    owner       = (uid, cid)
    zikr_type   = int(data["t"])
    icon, label = _TYPE_LABELS[zikr_type]
    bot.answer_callback_query(call.id)

    from utils.helpers import format_hour_arabic
    buttons = [
        btn(format_hour_arabic(h), "azkar_rem_save",
            {"t": zikr_type, "h": h, "m": 0},
            owner=owner, color="p")
        for h in range(24)
    ]
    buttons.append(btn("🔙 رجوع", "azkar_rem_add_type", {}, owner=owner, color="d"))
    edit_ui(call,
            text=f"{icon} <b>{label}</b>\n\nاختر الوقت (بتوقيتك المحلي):",
            buttons=buttons, layout=[3] * 8 + [1])


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
    from utils.helpers import format_hour_arabic
    time_label = format_hour_arabic(hour, minute)
    bot.answer_callback_query(
        call.id,
        f"✅ تم إضافة تذكير {label} على {time_label}",
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

    from utils.helpers import format_hour_arabic
    buttons = [
        btn(
            f"🗑 {_TYPE_LABELS.get(r['azkar_type'], ('📿', 'أذكار'))[0]} "
            f"{_TYPE_LABELS.get(r['azkar_type'], ('📿', 'أذكار'))[1]} "
            f"— {format_hour_arabic(r['hour'], r['minute'])}",
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

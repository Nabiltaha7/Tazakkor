"""
modules/quran/khatmah_reminder.py

Khatmah reminder logic.
The scheduler loop has been removed — reminders are now fired by the
unified IntervalScheduler in database/daily_tasks.py every 5 minutes.

Public API:
  fire_due_reminders(utc_hour, utc_minute) — called by the interval scheduler.
"""
from datetime import datetime, timezone

from core.bot import bot
from modules.quran import quran_db as db
from utils.pagination import btn
from utils.pagination.buttons import build_keyboard


def fire_due_reminders(utc_hour: int, utc_minute: int):
    """
    Sends khatmah reminders whose local time matches utc_hour:utc_minute.
    Called by the interval scheduler — no thread management here.
    """
    try:
        due = db.get_due_khatma_reminders(utc_hour, utc_minute)
        for r in due:
            _fire(r)
    except Exception as e:
        print(f"[KhatmahReminder] {e}")


def _fire(r: dict):
    uid   = r["user_id"]
    goal  = db.get_khatma_goal(uid)
    today = db.get_today_count(uid)

    if goal > 0 and today >= goal:
        return

    streak   = db.get_streak(uid)
    days_off = db.get_days_since_last_read(uid)

    if days_off >= 1:
        from modules.quran.khatmah import _inactive_msg
        extra_line = f"\n{_inactive_msg(days_off)}"
    elif streak >= 2:
        extra_line = f"\n🔥 حافظ على سلسلتك! ({streak} يوم)"
    else:
        extra_line = ""

    owner   = (uid, uid)
    buttons = [btn("▶️ متابعة القراءة", "kh_continue", {}, owner=owner, color="su")]
    markup  = build_keyboard(buttons, [1], uid)

    try:
        bot.send_message(
            uid,
            f"🕌 <b>تذكير الختمة</b>\n\n"
            f"📖 وردك اليومي ينتظرك"
            f"{extra_line}\n"
            f"🎯 هدفك: <b>{goal}</b> آية\n"
            f"📊 تقدمك اليوم: <b>{today}</b> / {goal}",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception:
        pass   # silent fail — user may have blocked the bot


# ── Backward-compat stub — no longer starts a thread ─────────────
def start_khatmah_reminder_scheduler():
    """Deprecated. Reminders are now handled by the unified IntervalScheduler."""
    pass

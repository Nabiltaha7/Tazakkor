"""
database/daily_tasks.py
────────────────────────
Scheduler job registration for all interval tasks.

All jobs are registered with core/scheduler.py via @register_interval.
No threads are created here — core/scheduler.py owns the thread lifecycle.

Interval jobs (every 5 min):
  - send_azkar                — periodic azkar broadcast to groups
  - fire_azkar_reminders      — personal azkar reminders
  - fire_group_azkar_reminders— group azkar schedule reminders
  - fire_khatmah_reminders    — khatmah reading reminders
  - send_kahf_friday_reminder — Friday Surah Al-Kahf reminder
  - refresh_config_cache      — refreshes bot_constants cache every 2 min
"""
from core.scheduler import register_interval
from database.connection import get_db_conn


# ══════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════

def _table_exists(name: str) -> bool:
    """Returns True if the named table exists in the PostgreSQL database."""
    try:
        cur = get_db_conn().cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (name,)
        )
        result = cur.fetchone() is not None
        cur.close()
        return result
    except Exception:
        return False


def _safe_run(fn) -> None:
    """
    Calls fn() and swallows missing-table errors silently.
    All other exceptions are logged with a traceback.
    """
    try:
        fn()
    except Exception as e:
        err = str(e)
        if "no such table" in err or "no such column" in err:
            print(f"⚠️ [daily_tasks] skipping {fn.__name__} (table/column missing)")
        else:
            import traceback
            print(f"❌ [daily_tasks] error in {fn.__name__}: {e}")
            traceback.print_exc()


# ══════════════════════════════════════════
# Config cache refresh (every cycle)
# ══════════════════════════════════════════

@register_interval
def refresh_config_cache() -> None:
    """
    Keeps the in-memory config cache fresh.
    core/config.py auto-refreshes every 120 s, but this ensures
    the scheduler also triggers a refresh on each 5-min cycle.
    """
    try:
        from core.config import force_refresh_config
        force_refresh_config()
    except Exception as e:
        print(f"[Config] Cache refresh error: {e}")


# ══════════════════════════════════════════
# Interval jobs (every 5 minutes)
# ══════════════════════════════════════════

@register_interval
def send_azkar() -> None:
    """Broadcasts periodic azkar to groups where azkar_enabled=1."""
    _safe_run(_do_send_azkar)


def _do_send_azkar() -> None:
    from modules.content_hub.azkar_sender import send_periodic_azkar
    send_periodic_azkar()


@register_interval
def fire_azkar_reminders() -> None:
    """Sends personal azkar reminders whose local time matches now."""
    if not _table_exists("azkar_reminders"):
        return
    _safe_run(_do_azkar_reminders)


def _do_azkar_reminders() -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    from database.db_queries.azkar_queries import get_due_azkar_reminders
    from modules.azkar.azkar_reminder import _fire_reminder
    for reminder in get_due_azkar_reminders(now.hour, now.minute):
        _fire_reminder(reminder)


@register_interval
def fire_group_azkar_reminders() -> None:
    """Sends scheduled group azkar reminders (morning/evening/sleep/wakeup)."""
    _safe_run(_do_group_azkar_reminders)


def _do_group_azkar_reminders() -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    from modules.azkar.azkar_reminder import fire_group_azkar_reminders
    fire_group_azkar_reminders(now.hour, now.minute)


@register_interval
def fire_khatmah_reminders() -> None:
    """Sends khatmah reminders whose local time matches now."""
    if not _table_exists("khatma_reminders"):
        return
    _safe_run(_do_khatmah_reminders)


def _do_khatmah_reminders() -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    from modules.quran.khatmah_reminder import fire_due_reminders
    fire_due_reminders(now.hour, now.minute)


# ══════════════════════════════════════════
# Friday Surah Al-Kahf reminder
# ══════════════════════════════════════════

_kahf_last_sent_date: str = ""

_KAHF_MESSAGE = (
    "📖 <b>تذكير بفضل سورة الكهف</b>\n"
    "─────────────────────\n\n"
    "عن أبي سعيد الخدري رضي الله عنه أن النبي ﷺ قال:\n"
    "<i>«مَن قرأ سورةَ الكهفِ في يومِ الجمعةِ، أضاءَ له من النورِ ما بينَ الجمعتين»</i>\n\n"
    "📌 اكتب <b>قراءة سورة</b> واختر سورة الكهف لقراءتها والحصول على الأجر."
)


@register_interval
def send_kahf_friday_reminder() -> None:
    """
    Sends the Surah Al-Kahf reminder every Friday.
    The trigger hour is read from bot_constants (KAHF_REMINDER_HOUR),
    interpreted as a local hour in UTC+3 (Yemen time).
    Fires every 5 min but sends only once per Friday.
    """
    global _kahf_last_sent_date
    from datetime import datetime, timezone, timedelta
    from core.config import get_config

    # Read configurable hour from DB cache (default: 7 = 07:00 Yemen)
    try:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    except (ValueError, TypeError):
        kahf_hour = 7

    _YEMEN_TZ = timezone(timedelta(hours=3))
    now       = datetime.now(_YEMEN_TZ)

    # Only on Friday (weekday 4) at the configured hour
    if now.weekday() != 4:
        return

    if now.hour != kahf_hour:
        return

    today = now.strftime("%Y-%m-%d")
    if _kahf_last_sent_date == today:
        return  # already sent this Friday

    print(f"[KAHF_TRIGGERED] Friday={today}, hour={kahf_hour}:00 Yemen time")
    _kahf_last_sent_date = today
    _safe_run(_do_send_kahf_reminder)


def _do_send_kahf_reminder() -> None:
    from core.bot import bot
    from database.db_queries.groups_queries import get_all_group_ids

    group_ids = get_all_group_ids()
    print(f"[KAHF_SCHEDULED] Sending to {len(group_ids)} groups...")

    sent    = 0
    failed  = 0
    for group_id in group_ids:
        try:
            bot.send_message(group_id, _KAHF_MESSAGE, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[KAHF_SENT] ❌ Failed for group {group_id}: {e}")

    print(f"[KAHF_SENT] ✅ Sent={sent}  ❌ Failed={failed}  Total={len(group_ids)}")


# ══════════════════════════════════════════
# Entry point — called once from main.py
# ══════════════════════════════════════════

def run_daily_tasks() -> None:
    """
    Called once at bot startup from main.py.
    The @register_interval decorators above have already registered all jobs
    when this module was imported. This function just confirms startup and
    logs the current Kahf reminder schedule.
    """
    from core.config import get_config
    try:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    except Exception:
        kahf_hour = 7

    print(f"[Scheduler] Interval jobs registered.")
    print(f"[KAHF_SCHEDULED] Kahf reminder configured for Friday "
          f"{kahf_hour:02d}:00 Yemen time (UTC+3).")

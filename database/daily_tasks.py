"""
database/daily_tasks.py
────────────────────────
Scheduler job registration for all timed features.

Jobs are registered with core/scheduler.py.  Three tiers:

  HourlyScheduler  (fires at :00 of every UTC hour)
  ─────────────────────────────────────────────────
  - check_kahf_friday_reminder   — Kahf reminder (Friday only, once per day)
  - check_group_azkar_reminders  — morning/evening/sleep/wakeup per group
  - check_khatmah_reminders      — personal khatmah reading reminders

  IntervalScheduler (fires every 5 minutes)
  ──────────────────────────────────────────
  - send_azkar                   — general azkar broadcast to groups
  - sync_config                  — incremental bot_constants sync

Separation rationale:
  - Hour-based features (reminders configured by hour, not minute) only need
    to run once per hour — no benefit from checking every 5 min.
  - General azkar broadcast uses per-group intervals (min 5 min) so it must
    stay on the 5-min ticker.
  - Config sync is lightweight and benefits from frequent checks.
"""
from core.scheduler import register_hourly, register_interval
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


def _safe_run(fn, *args) -> None:
    """
    Calls fn(*args) and swallows missing-table errors silently.
    All other exceptions are logged with a traceback.
    """
    try:
        fn(*args)
    except Exception as e:
        err = str(e)
        if "no such table" in err or "no such column" in err:
            print(f"⚠️ [daily_tasks] skipping {fn.__name__} (table/column missing)")
        else:
            import traceback
            print(f"❌ [daily_tasks] error in {fn.__name__}: {e}")
            traceback.print_exc()


# ══════════════════════════════════════════════════════════════════
# HOURLY JOBS — run once at the top of every UTC hour
# Each function receives utc_hour (int, 0–23).
# ══════════════════════════════════════════════════════════════════

# ── Friday Surah Al-Kahf reminder ────────────────────────────────

_kahf_last_sent_date: str = ""   # "YYYY-MM-DD" of the last Friday we sent

_KAHF_MESSAGE = (
    "📖 <b>تذكير بفضل سورة الكهف</b>\n"
    "─────────────────────\n\n"
   " عن أبي سعيد الخدري رضي الله عنه قال: قال رسول الله ﷺ: \n"
    "<b>«من قرأ سورة الكهف في يوم الجمعة، أضاء له من النور ما بين الجمعتين» </b> رواه الحاكم والبيهقي وصححه الألباني.\n\n"
    "📌 اكتب <code>قراءة سورة</code> واختر سورة الكهف لقراءتها والحصول على الأجر بإذن الله."
)


@register_hourly
def check_kahf_friday_reminder(utc_hour: int) -> None:
    """
    Hourly check — sends the Surah Al-Kahf reminder once per Friday.

    Logic:
      1. Convert utc_hour to Yemen local hour (UTC+3).
      2. Skip if today is not Friday.
      3. Skip if Yemen local hour ≠ KAHF_REMINDER_HOUR from bot_constants.
      4. Skip if already sent today (last_kahf_sent_date guard).
      5. Otherwise send to all groups and set the guard.
    """
    global _kahf_last_sent_date
    from datetime import datetime, timezone, timedelta
    from core.config import get_config

    _YEMEN_TZ  = timezone(timedelta(hours=3))
    now_yemen  = datetime.now(_YEMEN_TZ)
    yemen_hour = now_yemen.hour

    # Read target hour from in-memory config (loaded at startup)
    try:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    except (ValueError, TypeError):
        kahf_hour = 7

    # Only on Friday (weekday 4)
    if now_yemen.weekday() != 4:
        return

    # Hour must match
    if yemen_hour != kahf_hour:
        return

    today = now_yemen.strftime("%Y-%m-%d")
    if _kahf_last_sent_date == today:
        print(f"[KAHF_SCHEDULED] Already sent today ({today}) — skipping.")
        return

    print(
        f"[KAHF_TRIGGERED] Friday={today}, "
        f"Yemen={yemen_hour:02d}:00 (UTC={utc_hour:02d}:00), "
        f"target={kahf_hour:02d}:00 Yemen"
    )
    _kahf_last_sent_date = today
    _safe_run(_do_send_kahf_reminder)

def _do_send_kahf_reminder() -> None:
    from core.bot import bot
    from database.db_queries.groups_queries import get_all_group_ids

    group_ids = get_all_group_ids()
    print(f"[KAHF_SCHEDULED] Dispatching to {len(group_ids)} group(s)...")

    sent_count   = 0
    failed_count = 0

    for group_id in group_ids:
        try:
            sent_msg = bot.send_message(
                group_id,
                _KAHF_MESSAGE,
                parse_mode="HTML"
            )

            # تثبيت الرسالة
            try:
                bot.pin_chat_message(
                    group_id,
                    sent_msg.message_id,
                    disable_notification=True
                )
            except Exception as e:
                print(f"[KAHF_PIN] ⚠️ group={group_id}: {e}")

            sent_count += 1
            print(f"[KAHF_SENT] ✅ group={group_id}")

        except Exception as e:
            failed_count += 1
            print(f"[KAHF_SENT] ❌ group={group_id}: {e}")

    print(f"[KAHF_SENT] Summary — ✅ sent={sent_count}  ❌ failed={failed_count}  total={len(group_ids)}")

# ── Group azkar reminders (morning / evening / sleep / wakeup) ───

@register_hourly
def check_group_azkar_reminders(utc_hour: int) -> None:
    """
    Hourly check — sends group azkar reminders whose configured local hour
    matches the current UTC hour (after tz_offset conversion).

    Duplicate prevention is handled inside fire_group_azkar_reminders()
    via _sent_log keyed on (group_id, col, date+utc_hour).
    """
    _safe_run(_do_group_azkar_reminders, utc_hour)


def _do_group_azkar_reminders(utc_hour: int) -> None:
    from modules.azkar.azkar_reminder import fire_group_azkar_reminders
    # minute=0 — reminders are hour-only; no minute-level matching needed
    fire_group_azkar_reminders(utc_hour, 0)


# ── Khatmah reminders ────────────────────────────────────────────

@register_hourly
def check_khatmah_reminders(utc_hour: int) -> None:
    """
    Hourly check — sends khatmah reminders whose configured local hour
    matches the current UTC hour.
    """
    if not _table_exists("khatma_reminders"):
        return
    _safe_run(_do_khatmah_reminders, utc_hour)


def _do_khatmah_reminders(utc_hour: int) -> None:
    from modules.quran.khatmah_reminder import fire_due_reminders
    # minute=0 — reminders are hour-only
    fire_due_reminders(utc_hour, 0)


# ── Personal azkar reminders ─────────────────────────────────────

@register_hourly
def check_personal_azkar_reminders(utc_hour: int) -> None:
    """
    Hourly check — sends personal (user) azkar reminders whose configured
    local hour matches the current UTC hour.
    """
    if not _table_exists("azkar_reminders"):
        return
    _safe_run(_do_personal_azkar_reminders, utc_hour)


def _do_personal_azkar_reminders(utc_hour: int) -> None:
    from database.db_queries.azkar_queries import get_due_azkar_reminders
    from modules.azkar.azkar_reminder import _fire_reminder
    # minute=0 — reminders are hour-only
    for reminder in get_due_azkar_reminders(utc_hour, 0):
        _fire_reminder(reminder)


# ══════════════════════════════════════════════════════════════════
# INTERVAL JOBS — run every 5 minutes
# ══════════════════════════════════════════════════════════════════

# ── General azkar broadcast ───────────────────────────────────────

_MIN_AZKAR_INTERVAL_MIN = 5   # hard floor — no group may broadcast faster than this


@register_interval
def send_azkar() -> None:
    """
    Broadcasts general azkar content to groups where azkar_enabled=1.
    Each group's azkar_interval (minutes) is respected, with a hard
    minimum of 5 minutes to prevent spam.
    """
    _safe_run(_do_send_azkar)


def _do_send_azkar() -> None:
    from modules.content_hub.azkar_sender import send_periodic_azkar
    send_periodic_azkar()


# ── Incremental config sync ───────────────────────────────────────

@register_interval
def sync_config() -> None:
    """
    Incrementally syncs only changed bot_constants rows into memory.
    Uses updated_at column — no full reload, zero work when nothing changed.
    """
    try:
        from core.config import sync_changed_constants
        sync_changed_constants()
    except Exception as e:
        print(f"[Config] Incremental sync error: {e}")


# ══════════════════════════════════════════════════════════════════
# Entry point — called once from main.py
# ══════════════════════════════════════════════════════════════════

def run_daily_tasks() -> None:
    """
    Called once at bot startup from main.py after load_config_on_startup().
    All @register_hourly / @register_interval decorators above have already
    registered their jobs when this module was imported.

    Prints a startup summary of the configured schedule.
    """
    from core.config import get_config
    try:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    except Exception:
        kahf_hour = 7

    print("[Scheduler] Hourly jobs  : check_kahf_friday_reminder, "
          "check_group_azkar_reminders, check_khatmah_reminders, "
          "check_personal_azkar_reminders")
    print("[Scheduler] Interval jobs: send_azkar (every 5 min), "
          "sync_config (every 5 min)")
    print(
        f"[KAHF_SCHEDULED] Kahf reminder → Friday "
        f"{kahf_hour:02d}:00 Yemen time (UTC {(kahf_hour - 3) % 24:02d}:00). "
        f"Checked once per hour."
    )

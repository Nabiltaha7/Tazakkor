"""
core/scheduler.py — Unified scheduling system

Three schedulers, one thread each:

  DailyScheduler    — fires once per day at midnight Yemen time (UTC+3).
                      Use for heavy resets: daily tasks, data cleanup, seasons, etc.

  HourlyScheduler   — fires once at the top of every UTC hour (:00).
                      Use for hour-based checks: Kahf reminder, group azkar
                      reminders (morning/evening/sleep/wakeup), khatmah reminders.
                      Jobs receive (utc_hour: int) as their only argument.

  IntervalScheduler — fires every INTERVAL_SECONDS (default 300 = 5 min).
                      Use for sub-hour recurring work: general azkar broadcast,
                      config sync, etc.

Usage:
    from core.scheduler import daily, hourly, interval

    @daily
    def my_midnight_job():
        ...

    @hourly
    def my_hourly_job(utc_hour: int):
        ...

    @interval
    def my_5min_job():
        ...

All decorators register the function and start the scheduler thread
automatically on first registration. Thread-safe. One thread per scheduler.
"""

import threading
import time
import traceback
from datetime import datetime, timezone, timedelta

# ── Yemen timezone (UTC+3) ────────────────────────────────────────
_YEMEN_TZ = timezone(timedelta(hours=3))

# ── Interval in seconds for the interval scheduler ───────────────
INTERVAL_SECONDS = 300   # 5 minutes


# ══════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════

_daily_jobs:   list[callable] = []
_hourly_jobs:  list[callable] = []
_interval_jobs: list[callable] = []

_daily_started    = False
_hourly_started   = False
_interval_started = False
_lock = threading.Lock()


def daily(fn: callable) -> callable:
    """Decorator — registers fn to run once per day at midnight Yemen time."""
    with _lock:
        _daily_jobs.append(fn)
        _ensure_daily_started()
    return fn


def hourly(fn: callable) -> callable:
    """
    Decorator — registers fn to run once at the top of every UTC hour.
    fn must accept a single positional argument: utc_hour (int, 0–23).
    """
    with _lock:
        _hourly_jobs.append(fn)
        _ensure_hourly_started()
    return fn


def interval(fn: callable) -> callable:
    """Decorator — registers fn to run every INTERVAL_SECONDS (5 min)."""
    with _lock:
        _interval_jobs.append(fn)
        _ensure_interval_started()
    return fn


def register_daily(fn: callable):
    """Imperative alternative to @daily decorator."""
    return daily(fn)


def register_hourly(fn: callable):
    """Imperative alternative to @hourly decorator."""
    return hourly(fn)


def register_interval(fn: callable):
    """Imperative alternative to @interval decorator."""
    return interval(fn)


# ══════════════════════════════════════════════════════════════════
# Scheduler threads
# ══════════════════════════════════════════════════════════════════

def _ensure_daily_started():
    global _daily_started
    if not _daily_started:
        _daily_started = True
        t = threading.Thread(target=_daily_loop, daemon=True, name="DailyScheduler")
        t.start()


def _ensure_hourly_started():
    global _hourly_started
    if not _hourly_started:
        _hourly_started = True
        t = threading.Thread(target=_hourly_loop, daemon=True, name="HourlyScheduler")
        t.start()


def _ensure_interval_started():
    global _interval_started
    if not _interval_started:
        _interval_started = True
        t = threading.Thread(target=_interval_loop, daemon=True, name="IntervalScheduler")
        t.start()


def _seconds_until_midnight() -> float:
    """Seconds until next midnight in Yemen timezone."""
    now      = datetime.now(_YEMEN_TZ)
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1.0, (midnight - now).total_seconds())


def _seconds_until_next_hour() -> float:
    """Seconds until the top of the next UTC hour (:00:00)."""
    now = datetime.now(timezone.utc)
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return max(1.0, (next_hour - now).total_seconds())


def _daily_loop():
    """
    Sleeps until the next Yemen midnight, then runs all daily jobs.
    Repeats forever.
    """
    while True:
        delay = _seconds_until_midnight()
        print(f"[DailyScheduler] Next run in {delay/3600:.2f}h "
              f"({datetime.now(_YEMEN_TZ).strftime('%Y-%m-%d')} Yemen)")
        time.sleep(delay)
        _run_jobs(_daily_jobs, "DailyScheduler")


def _hourly_loop():
    """
    Sleeps until the top of the next UTC hour, then runs all hourly jobs.
    Passes the current UTC hour (int) to each job.
    Repeats forever.
    """
    while True:
        delay = _seconds_until_next_hour()
        print(f"[HourlyScheduler] Next run in {delay/60:.1f}min "
              f"(UTC {datetime.now(timezone.utc).strftime('%H:%M')})")
        time.sleep(delay)
        utc_hour = datetime.now(timezone.utc).hour
        _run_hourly_jobs(utc_hour)


def _interval_loop():
    """
    Runs all interval jobs every INTERVAL_SECONDS.
    Aligns to the top of the minute on first run.
    """
    # align to next clean minute boundary
    time.sleep(60 - datetime.now().second)

    while True:
        _run_jobs(_interval_jobs, "IntervalScheduler")
        time.sleep(INTERVAL_SECONDS)


def _run_jobs(jobs: list, label: str):
    snapshot = list(jobs)   # copy under no lock — reads are safe
    for fn in snapshot:
        try:
            fn()
        except Exception as e:
            print(f"[{label}] Error in {fn.__name__}: {e}")
            traceback.print_exc()


def _run_hourly_jobs(utc_hour: int):
    snapshot = list(_hourly_jobs)
    for fn in snapshot:
        try:
            fn(utc_hour)
        except Exception as e:
            print(f"[HourlyScheduler] Error in {fn.__name__}: {e}")
            traceback.print_exc()


# ══════════════════════════════════════════════════════════════════
# Manual trigger (for testing / admin panel)
# ══════════════════════════════════════════════════════════════════

def trigger_daily_now():
    """Runs all daily jobs immediately (for testing or manual reset)."""
    _run_jobs(_daily_jobs, "DailyScheduler[manual]")


def trigger_hourly_now():
    """Runs all hourly jobs immediately with the current UTC hour."""
    utc_hour = datetime.now(timezone.utc).hour
    _run_hourly_jobs(utc_hour)


def trigger_interval_now():
    """Runs all interval jobs immediately."""
    _run_jobs(_interval_jobs, "IntervalScheduler[manual]")

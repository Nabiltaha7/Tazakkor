import os
import threading
import time
from dotenv import load_dotenv
load_dotenv()

# =========================
# ENVIRONMENT
# =========================
IS_TEST = os.environ.get("IS_TEST", "false").lower() == "true"

# =========================
# TOKENS
# =========================
if IS_TEST:
    TOKEN = os.environ.get("TEST_TOKEN")
else:
    TOKEN = os.environ.get("BOT_TOKEN")

# =========================
# DATABASE — PostgreSQL only (Supabase)
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set.\n"
        "Add it to your .env file (local) or Render environment variables (production).\n"
        "Format: postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
    )

# =========================
# OTHER
# =========================
developers_id = {7632471789, 8168497909}
bot_name = "تَذَكُّر | 𝐓𝐚𝐳𝐚𝐤𝐤𝐨𝐫"

# Bot command prefix (for flexible command matching)
BOT_NAME = "تذكره"

# =========================
# STARTUP LOG
# =========================
print("🌐 Running in PRODUCTION mode  (PostgreSQL / Supabase)")
if IS_TEST:
    print("🧪 TEST MODE active")


# ══════════════════════════════════════════════════════════════════════════════
# Dynamic config cache — loaded ONCE at startup, then updated incrementally
#
# Strategy (Option A):
#   - load_config_on_startup() loads ALL constants once into _config_cache.
#   - sync_changed_constants() polls only rows WHERE updated_at > _last_sync_ts
#     and updates only those keys — zero full reloads after startup.
#   - set_config() updates a single key in memory immediately after a DB write.
#   - get_config() reads from the in-memory dict — no DB hit, no staleness check.
# ══════════════════════════════════════════════════════════════════════════════

_config_cache: dict[str, str] = {}
_cache_lock   = threading.Lock()
_last_sync_ts: int = 0   # Unix timestamp of the most-recently synced row


def get_config(key: str, default: str = None) -> str | None:
    """
    Returns a config value from the in-memory cache.
    The cache is populated once at startup and kept current via
    sync_changed_constants() — no DB hit on every call.

    Usage:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    """
    with _cache_lock:
        return _config_cache.get(key, default)


def set_config(key: str, value: str) -> None:
    """
    Updates a single key in the in-memory cache immediately.
    Call this right after writing a new value to bot_constants so the
    change is visible to all threads without waiting for the next sync.

    Usage:
        set_bot_constant("KAHF_REMINDER_HOUR", "8")
        set_config("KAHF_REMINDER_HOUR", "8")
    """
    with _cache_lock:
        _config_cache[key] = value


def load_config_on_startup() -> None:
    """
    Loads ALL bot_constants into memory exactly once at bot startup.
    Sets _last_sync_ts to the maximum updated_at seen so that subsequent
    sync_changed_constants() calls only fetch newer rows.

    Called from main.py after DB tables are created.
    """
    global _last_sync_ts
    try:
        from database.connection import db_fetchall
        rows = db_fetchall(
            "SELECT name, value, updated_at FROM bot_constants"
        )
        with _cache_lock:
            _config_cache.clear()
            max_ts = 0
            for row in rows:
                _config_cache[row["name"]] = row["value"]
                ts = row.get("updated_at") or 0
                if ts and ts > max_ts:
                    max_ts = ts
            _last_sync_ts = max_ts
        print(f"[Config] Loaded {len(rows)} constants on startup "
              f"(last updated_at={_last_sync_ts}).")
    except Exception as e:
        print(f"[Config] Startup load failed: {e}")


def sync_changed_constants() -> None:
    """
    Fetches ONLY rows whose updated_at > _last_sync_ts and updates
    those keys in memory.  Zero DB work when nothing has changed.

    Called by the interval scheduler (e.g. every 5 min).
    Does NOT do a full reload — only touches changed keys.
    """
    global _last_sync_ts
    try:
        from database.connection import db_fetchall
        rows = db_fetchall(
            "SELECT name, value, updated_at FROM bot_constants "
            "WHERE updated_at > %s",
            (_last_sync_ts,)
        )
        if not rows:
            return  # nothing changed — no work done

        with _cache_lock:
            max_ts = _last_sync_ts
            for row in rows:
                _config_cache[row["name"]] = row["value"]
                ts = row.get("updated_at") or 0
                if ts > max_ts:
                    max_ts = ts
            _last_sync_ts = max_ts

        print(f"[Config] Synced {len(rows)} changed constant(s) "
              f"(new last_sync_ts={_last_sync_ts}).")
    except Exception as e:
        print(f"[Config] Incremental sync failed: {e}")


def force_refresh_config() -> None:
    """
    Forces a full reload of all constants from the database.
    Use sparingly — prefer sync_changed_constants() for routine updates.
    Resets _last_sync_ts to the new maximum so incremental sync stays correct.
    """
    global _last_sync_ts
    try:
        from database.connection import db_fetchall
        rows = db_fetchall(
            "SELECT name, value, updated_at FROM bot_constants"
        )
        with _cache_lock:
            _config_cache.clear()
            max_ts = 0
            for row in rows:
                _config_cache[row["name"]] = row["value"]
                ts = row.get("updated_at") or 0
                if ts and ts > max_ts:
                    max_ts = ts
            _last_sync_ts = max_ts
        print(f"[Config] Force-refreshed {len(rows)} constants "
              f"(last_sync_ts={_last_sync_ts}).")
    except Exception as e:
        print(f"[Config] Force refresh failed: {e}")

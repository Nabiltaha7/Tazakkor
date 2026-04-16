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
# Dynamic config cache — loaded from bot_constants table
# ══════════════════════════════════════════════════════════════════════════════

_config_cache: dict[str, str] = {}
_cache_lock = threading.Lock()
_last_refresh: float = 0
_REFRESH_INTERVAL = 120  # seconds — refresh every 2 minutes


def get_config(key: str, default: str = None) -> str | None:
    """
    Returns a config value from the cached bot_constants.
    Auto-refreshes the cache every 2 minutes.
    
    Usage:
        kahf_hour = int(get_config("KAHF_REMINDER_HOUR", "7"))
    """
    global _last_refresh
    now = time.time()
    
    with _cache_lock:
        # Refresh if cache is empty or stale
        if not _config_cache or (now - _last_refresh) > _REFRESH_INTERVAL:
            _refresh_config_cache()
            _last_refresh = now
        
        return _config_cache.get(key, default)


def _refresh_config_cache() -> None:
    """
    Reloads all bot_constants from the database into memory.
    Called automatically by get_config() when cache is stale.
    Thread-safe (must be called under _cache_lock).
    """
    try:
        from database.db_queries.reports_queries import get_all_constants
        constants = get_all_constants()
        _config_cache.clear()
        for c in constants:
            _config_cache[c["name"]] = c["value"]
        print(f"[Config] Refreshed {len(_config_cache)} constants from database.")
    except Exception as e:
        print(f"[Config] Failed to refresh cache: {e}")


def force_refresh_config() -> None:
    """
    Forces an immediate config cache refresh.
    Use after updating bot_constants in the database.
    """
    global _last_refresh
    with _cache_lock:
        _refresh_config_cache()
        _last_refresh = time.time()

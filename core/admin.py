"""
core/admin.py
──────────────
Bot constants cache and developer role management.

Rules:
  - No direct SQL here — all DB access goes through db_queries layer.
  - This module is the single source of truth for developer checks.
"""
import time
from database.db_queries.reports_queries import (
    get_bot_constant,
    set_bot_constant,
    get_all_constants as _db_get_all_constants,
    get_all_developers as _db_get_all_devs,
    upsert_developer,
    remove_developer_db,
    get_developer,
)
from core.config import developers_id as _DEFAULT_DEVS


# ══════════════════════════════════════════
# Bot constants (with cache)
# ══════════════════════════════════════════

_CONST_CACHE: dict[str, str] = {}
_CACHE_TS:    float = 0
_CACHE_TTL:   float = 60.0


def _load_constants() -> None:
    global _CONST_CACHE, _CACHE_TS
    try:
        from database.db_queries.reports_queries import get_all_constants as _fetch
        rows = _fetch()
        _CONST_CACHE = {r["name"]: r["value"] for r in rows}
        _CACHE_TS    = time.time()
    except Exception:
        pass


def get_const(name: str, default=None):
    """Returns a bot constant from cache or DB."""
    if time.time() - _CACHE_TS > _CACHE_TTL:
        _load_constants()
    val = _CONST_CACHE.get(name)
    return val if val is not None else default


def get_const_int(name: str, default: int = 0) -> int:
    try:
        return int(get_const(name, default))
    except (ValueError, TypeError):
        return default


def get_const_float(name: str, default: float = 0.0) -> float:
    try:
        return float(get_const(name, default))
    except (ValueError, TypeError):
        return default


def set_const(name: str, value: str) -> bool:
    """Updates a bot constant in DB and invalidates cache."""
    global _CACHE_TS
    try:
        set_bot_constant(name, str(value))
        _CACHE_TS = 0   # invalidate cache
        return True
    except Exception:
        return False


def get_all_constants() -> list:
    """Returns all bot constants for display."""
    try:
        return _db_get_all_constants()
    except Exception:
        return []


# ══════════════════════════════════════════
# Developer roles
# ══════════════════════════════════════════

def is_primary_dev(user_id: int) -> bool:
    if user_id in _DEFAULT_DEVS:
        return True
    try:
        dev = get_developer(user_id)
        return dev is not None and dev.get("role") == "primary"
    except Exception:
        return False


def is_secondary_dev(user_id: int) -> bool:
    try:
        dev = get_developer(user_id)
        return dev is not None and dev.get("role") == "secondary"
    except Exception:
        return False


def is_any_dev(user_id: int) -> bool:
    return is_primary_dev(user_id) or is_secondary_dev(user_id)


def get_all_developers() -> list:
    try:
        return _db_get_all_devs()
    except Exception:
        return []


def add_developer(user_id: int, role: str = "secondary") -> bool:
    try:
        upsert_developer(user_id, role)
        return True
    except Exception:
        return False


def remove_developer(user_id: int) -> bool:
    if user_id in _DEFAULT_DEVS:
        return False
    try:
        return remove_developer_db(user_id)
    except Exception:
        return False


def promote_developer(user_id: int) -> bool:
    return add_developer(user_id, "primary")


def demote_developer(user_id: int) -> bool:
    if user_id in _DEFAULT_DEVS:
        return False
    return add_developer(user_id, "secondary")

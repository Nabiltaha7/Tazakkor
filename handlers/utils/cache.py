"""
handlers/utils/cache.py
────────────────────────
Simple per-user in-memory cache for handler-level data.
TTL-based eviction on read.

For pagination button caching, see utils/pagination/cache.py.
"""
import time
from typing import Any, Optional

_CACHE: dict[int, tuple[Any, float]] = {}
CACHE_TTL = 600  # 10 minutes


def get_cache(user_id: int) -> Optional[Any]:
    """Returns cached data for user_id, or None if expired/missing."""
    entry = _CACHE.get(user_id)
    if entry is None:
        return None
    data, ts = entry
    if time.time() - ts < CACHE_TTL:
        return data
    _CACHE.pop(user_id, None)
    return None


def set_cache(user_id: int, data: Any) -> None:
    """Stores data for user_id with current timestamp."""
    _CACHE[user_id] = (data, time.time())


def clear_cache(user_id: int) -> None:
    """Removes cached data for user_id."""
    _CACHE.pop(user_id, None)

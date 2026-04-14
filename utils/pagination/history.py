"""
utils/pagination/history.py
────────────────────────────
Per-user navigation history for the "back" button.

History entries are evicted after HISTORY_TTL seconds of inactivity
to prevent unbounded memory growth.
"""
import time
from .router import register_action
from core.bot import bot

# Max history depth per user+chat pair
_MAX_DEPTH   = 20
# Evict entries older than this (seconds)
_HISTORY_TTL = 3600   # 1 hour

# (user_id, chat_id) → {"entries": [...], "last_active": float}
_HISTORY: dict[tuple, dict] = {}


def push_history(
    user_id: int,
    chat_id: int,
    text: str,
    buttons: list,
    layout: list,
    precheck=None,
) -> None:
    """Pushes a page onto the user's navigation history."""
    key   = (user_id, chat_id)
    entry = {"text": text, "buttons": buttons, "layout": layout, "precheck": precheck}

    if key not in _HISTORY:
        _HISTORY[key] = {"entries": [], "last_active": time.time()}

    bucket = _HISTORY[key]
    bucket["entries"].append(entry)
    bucket["last_active"] = time.time()

    # Cap depth
    if len(bucket["entries"]) > _MAX_DEPTH:
        bucket["entries"] = bucket["entries"][-_MAX_DEPTH:]

    # Periodic eviction of stale buckets
    _evict()


def _evict() -> None:
    """Removes history buckets that haven't been touched in _HISTORY_TTL seconds."""
    now     = time.time()
    stale   = [k for k, v in _HISTORY.items() if now - v["last_active"] > _HISTORY_TTL]
    for k in stale:
        del _HISTORY[k]


@register_action("back")
def go_back(call, data):
    from .ui import edit_ui

    key     = (call.from_user.id, call.message.chat.id)
    bucket  = _HISTORY.get(key)
    entries = bucket["entries"] if bucket else []

    if len(entries) < 2:
        bot.answer_callback_query(call.id, "لا يوجد رجوع")
        return

    entries.pop()
    prev = entries[-1]
    edit_ui(call, prev["text"], prev["buttons"], prev["layout"], prev.get("precheck"))

# utils/pagination/router.py
import time
from core.bot import bot
from .cache import get_cache

# ── Action handlers ──
ACTION_HANDLERS = {}

_ERR_ICON = "❌"   # inline — avoids importing utils.helpers (circular risk)


def register_action(name: str):
    def decorator(func):
        ACTION_HANDLERS[name] = func
        return func
    return decorator


# ══════════════════════════════════════════
# State — delegates to StateManager
# ══════════════════════════════════════════
# Backward-compatible shim: all existing set_state/get_state/clear_state
# calls continue to work, but now use the central StateManager.

def set_state(user_id, chat_id, state: str, data: dict = None, precheck=None,
              ttl: int = 300):
    """
    Backward-compatible wrapper.
    Stores state in the new StateManager format:
      {"type": state, "step": None, "mid": data.get("_mid"), "extra": data}
    """
    from core.state_manager import StateManager
    d = data or {}
    StateManager.set(user_id, chat_id, {
        "type":  state,
        "step":  d.pop("_step", None),
        "mid":   d.pop("_mid", None),
        "extra": d,
    }, ttl=ttl)


def get_state(user_id, chat_id) -> dict:
    """
    Backward-compatible wrapper.
    Returns the old-style dict: {"state": type, "data": extra+mid}
    so existing code that does state["state"] and state.get("data", {}) still works.
    """
    from core.state_manager import StateManager
    s = StateManager.get(user_id, chat_id)
    if not s:
        return {}
    # Reconstruct old-style dict
    data = dict(s.get("extra") or {})
    if s.get("mid") is not None:
        data["_mid"] = s["mid"]
    if s.get("step") is not None:
        data["_step"] = s["step"]
    return {"state": s["type"], "data": data}


def clear_state(user_id, chat_id):
    from core.state_manager import StateManager
    StateManager.clear(user_id, chat_id)


def is_busy(user_id, chat_id) -> bool:
    from core.state_manager import StateManager
    return StateManager.exists(user_id, chat_id)


# ══════════════════════════════════════════
# Pagination
# ══════════════════════════════════════════

def paginate_list(items, page=0, per_page=10):
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    start = page * per_page
    end   = start + per_page
    return items[start:end], total_pages


# ══════════════════════════════════════════
# Callback handler
# ══════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("k:"))
def handle_buttons(call):
    data = call.data
    key = data.split(":", 1)[1]

    from .cache import _CACHE, _CACHE_LOCK, CACHE_TTL
    with _CACHE_LOCK:
        entry = _CACHE.get(key)

    if not entry:
        bot.answer_callback_query(
            call.id, "⏳ هذا الزر انتهت صلاحيته", show_alert=True
        )
        return

    if time.time() - entry["ts"] > CACHE_TTL:
        bot.answer_callback_query(
            call.id, "⏳ هذا الزر انتهت صلاحيته", show_alert=True
        )
        return

    owner = entry.get("owner")
    if owner:
        owner_uid, owner_cid = owner
        if owner_uid != call.from_user.id:
            bot.answer_callback_query(call.id, f"{_ERR_ICON} هذا الزر ليس لك", show_alert=True)
            return
        if owner_cid is not None and owner_cid != call.message.chat.id:
            bot.answer_callback_query(call.id, f"{_ERR_ICON} هذا الزر ليس لك", show_alert=True)
            return

    payload = entry["data"]
    action  = payload.get("a")
    extra   = payload.get("d", {})
    handler = ACTION_HANDLERS.get(action)
    if handler:
        handler(call, extra)
    else:
        bot.answer_callback_query(call.id, f"⚠️ لا يوجد إجراء: {action}")

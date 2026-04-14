import time
import threading
import uuid

_CACHE = {}
_CACHE_LOCK = threading.Lock()
CACHE_TTL = 259200  # 3 أيام (72 ساعة)

def store_cache(user_id: int, chat_id: int, payload: dict, owner=None) -> str:
    key = uuid.uuid4().hex[:12]
    with _CACHE_LOCK:
        evict_cache()
        _CACHE[key] = {
            "uid": user_id,
            "cid": chat_id,
            "data": payload,
            "owner": owner,
            "ts": time.time()
        }
    return key

def get_cache(key: str, user_id: int, chat_id: int):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL:
        with _CACHE_LOCK:
            _CACHE.pop(key, None)
        return None
    owner = entry.get("owner")
    if owner:
        owner_uid, owner_cid = owner
        # always check user — check chat only if it was stored
        if owner_uid != user_id:
            return None
        if owner_cid is not None and owner_cid != chat_id:
            return None
    return entry["data"]

def evict_cache():
    now = time.time()
    expired = [k for k, v in _CACHE.items() if now - v["ts"] > CACHE_TTL]
    for k in expired:
        del _CACHE[k]
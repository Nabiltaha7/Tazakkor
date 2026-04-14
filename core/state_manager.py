"""
StateManager — نظام إدارة الحالة المركزي
يستبدل كل القواميس المبعثرة وset_state/get_state القديمة.

صيغة الحالة الموحدة:
{
    "type":  "qr_add",        # نوع الحالة (مطلوب)
    "step":  "await_sura",    # الخطوة الحالية (اختياري)
    "mid":   message_id,      # معرف الرسالة للتعديل (اختياري)
    "extra": {}               # بيانات إضافية (اختياري)
}
"""
import threading
import time
from typing import Optional
from utils.logger import log_event

# ── الثوابت ──
DEFAULT_TTL = 300   # 5 دقائق افتراضياً
_LOCK       = threading.Lock()
_STORE: dict[tuple, dict] = {}   # (user_id, chat_id) → {state, expires_at}


class StateManager:
    """
    مدير الحالة المركزي — thread-safe، مع TTL تلقائي.
    """

    # ══════════════════════════════════════════
    # العمليات الأساسية
    # ══════════════════════════════════════════

    @staticmethod
    def set(user_id: int, chat_id: int, data: dict, ttl: int = DEFAULT_TTL):
        """
        يحفظ حالة جديدة.
        data يجب أن يحتوي على "type" على الأقل.
        """
        if "type" not in data:
            raise ValueError("StateManager.set: data must contain 'type'")
        key = (user_id, chat_id)
        entry = {
            "state":      data,
            "expires_at": time.time() + ttl,
        }
        with _LOCK:
            _STORE[key] = entry
        log_event("state_set", user=user_id, chat=chat_id, type=data.get("type"), step=data.get("step"))

    @staticmethod
    def get(user_id: int, chat_id: int) -> Optional[dict]:
        """
        يرجع الحالة الحالية أو None إذا انتهت صلاحيتها أو لم تكن موجودة.
        """
        key = (user_id, chat_id)
        with _LOCK:
            entry = _STORE.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            with _LOCK:
                _STORE.pop(key, None)
            return None
        return entry["state"]

    @staticmethod
    def clear(user_id: int, chat_id: int):
        """يمسح الحالة."""
        with _LOCK:
            _STORE.pop((user_id, chat_id), None)
        log_event("state_clear", user=user_id, chat=chat_id)

    @staticmethod
    def exists(user_id: int, chat_id: int) -> bool:
        """يتحقق من وجود حالة نشطة."""
        return StateManager.get(user_id, chat_id) is not None

    @staticmethod
    def update(user_id: int, chat_id: int, new_data: dict):
        """
        يُحدّث حقولاً في الحالة الحالية دون مسحها.
        يُنشئ حالة جديدة إذا لم تكن موجودة.
        """
        key = (user_id, chat_id)
        with _LOCK:
            entry = _STORE.get(key)
        if entry and time.time() <= entry["expires_at"]:
            entry["state"].update(new_data)
        else:
            # لا توجد حالة — أنشئ واحدة جديدة إذا كان new_data يحتوي على type
            if "type" in new_data:
                StateManager.set(user_id, chat_id, new_data)

    # ══════════════════════════════════════════
    # مساعدات النوع والخطوة
    # ══════════════════════════════════════════

    @staticmethod
    def is_state(user_id: int, chat_id: int, state_type: str) -> bool:
        """
        يرجع True إذا كانت الحالة موجودة ونوعها == state_type.
        """
        state = StateManager.get(user_id, chat_id)
        return state is not None and state.get("type") == state_type

    @staticmethod
    def get_step(user_id: int, chat_id: int) -> Optional[str]:
        """يرجع الخطوة الحالية."""
        state = StateManager.get(user_id, chat_id)
        return state.get("step") if state else None

    @staticmethod
    def set_step(user_id: int, chat_id: int, step: str):
        """يُحدّث الخطوة الحالية."""
        StateManager.update(user_id, chat_id, {"step": step})
        state = StateManager.get(user_id, chat_id)
        log_event("flow_step", user=user_id, chat=chat_id, step=step, type=state.get("type") if state else None)

    # ══════════════════════════════════════════
    # مساعدات الـ mid
    # ══════════════════════════════════════════

    @staticmethod
    def get_mid(user_id: int, chat_id: int) -> Optional[int]:
        """يرجع معرف الرسالة المحفوظة."""
        state = StateManager.get(user_id, chat_id)
        return state.get("mid") if state else None

    @staticmethod
    def set_mid(user_id: int, chat_id: int, mid: int):
        """يُحدّث معرف الرسالة."""
        StateManager.update(user_id, chat_id, {"mid": mid})

    # ══════════════════════════════════════════
    # مساعدات الـ extra
    # ══════════════════════════════════════════

    @staticmethod
    def get_extra(user_id: int, chat_id: int) -> dict:
        """يرجع البيانات الإضافية."""
        state = StateManager.get(user_id, chat_id)
        return (state.get("extra") or {}) if state else {}

    # ══════════════════════════════════════════
    # أدوات التشخيص والمساعدة
    # ══════════════════════════════════════════

    @staticmethod
    def debug_state(user_id: int, chat_id: int) -> dict:
        """يرجع الحالة الكاملة للتشخيص."""
        return StateManager.get(user_id, chat_id) or {}

    @staticmethod
    def clear_if_type(user_id: int, chat_id: int, state_type: str):
        """يمسح الحالة فقط إذا كان نوعها مطابقاً."""
        if StateManager.is_state(user_id, chat_id, state_type):
            StateManager.clear(user_id, chat_id)

    @staticmethod
    def cleanup_expired():
        """يُنظّف الحالات المنتهية — يمكن استدعاؤه دورياً."""
        now = time.time()
        with _LOCK:
            expired = [k for k, v in _STORE.items() if now > v["expires_at"]]
            for k in expired:
                del _STORE[k]
        return len(expired)


# ── instance عام للاستخدام المباشر ──
state_manager = StateManager()


# ══════════════════════════════════════════
# 🔁 تنظيف تلقائي في الخلفية
# ══════════════════════════════════════════

def _state_gc_loop():
    while True:
        try:
            StateManager.cleanup_expired()
        except Exception:
            pass
        time.sleep(60)


_gc_thread = threading.Thread(target=_state_gc_loop, daemon=True, name="StateGC")
_gc_thread.start()

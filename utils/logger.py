"""
نظام التسجيل المركزي — log_event
"""
import time


def log_event(event: str, **data):
    """
    يسجّل حدثاً مع بياناته.
    الاستخدام:
        log_event("state_set", user=uid, type=state_type)
        log_event("flow_step", step=step, type=state_type)
        log_event("db_delete_attempt", attempt=i)
        log_event("error", error=str(e))
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    parts = ", ".join(f"{k}={v!r}" for k, v in data.items())
    print(f"[{ts}] [{event}] {parts}")

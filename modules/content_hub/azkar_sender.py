"""
modules/content_hub/azkar_sender.py
─────────────────────────────────────
يرسل أذكاراً دورية للمجموعات التي فعّلت azkar_enabled.
يُشغَّل كل 5 دقائق من المُجدوِل.
"""
import time

from core.bot import bot
from database.db_queries.azkar_queries import get_random_azkar_content
from database.db_queries.groups_queries import get_all_group_ids, get_group_setting, set_group_setting

# throttle: group_id → last_sent_unix
_last_sent: dict[int, float] = {}


def _get_interval_seconds() -> int:
    """يقرأ azkar_interval_minutes من bot_constants. الافتراضي 10 دقائق."""
    try:
        from core.admin import get_const_int
        return get_const_int("azkar_interval_minutes", 10) * 60
    except Exception:
        return 600


def send_periodic_azkar():
    """
    يُرسَل من المُجدوِل كل 5 دقائق.
    يرسل ذكراً لكل مجموعة فعّلت azkar_enabled مع احترام الفترة الزمنية لكل مجموعة.
    """
    now = time.time()

    try:
        group_ids = get_all_group_ids()
    except Exception:
        return

    for tg_group_id in group_ids:
        try:
            enabled  = get_group_setting(tg_group_id, "azkar_enabled")
            if not enabled:
                continue

            # فترة الإرسال الخاصة بالمجموعة (بالدقائق)، افتراضي 15
            interval_min = get_group_setting(tg_group_id, "azkar_interval") or 15
            interval_sec = int(interval_min) * 60

            if now - _last_sent.get(tg_group_id, 0) < interval_sec:
                continue

            row = get_random_azkar_content()
            if not row:
                continue

            bot.send_message(tg_group_id, f"📿\n\n{row['content']}", parse_mode="HTML")
            _last_sent[tg_group_id] = now
        except Exception as e:
            print(f"[AzkarSender] فشل الإرسال للمجموعة {tg_group_id}: {e}")


def toggle_azkar(tg_group_id: int, enable: bool) -> bool:
    """يُفعّل أو يوقف الأذكار التلقائية للمجموعة."""
    try:
        ok = set_group_setting(tg_group_id, "azkar_enabled", 1 if enable else 0)
    except Exception:
        return False
    if ok and not enable:
        _last_sent.pop(tg_group_id, None)
    return ok


def is_azkar_enabled(tg_group_id: int) -> bool:
    try:
        return bool(get_group_setting(tg_group_id, "azkar_enabled"))
    except Exception:
        return False

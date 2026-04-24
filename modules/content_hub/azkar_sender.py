"""
modules/content_hub/azkar_sender.py
─────────────────────────────────────
يرسل أذكاراً دورية للمجموعات التي فعّلت azkar_enabled.
يُشغَّل كل 5 دقائق من المُجدوِل.

قاعدة: الحد الأدنى للفترة الزمنية بين الإرسالين = 5 دقائق.
أي قيمة أقل من 5 في azkar_interval تُعامَل كـ 5.
"""
import time

from core.bot import bot
from database.db_queries.azkar_queries import get_random_azkar_content
from database.db_queries.groups_queries import get_all_group_ids, get_group_setting, set_group_setting

# throttle: group_id → last_sent_unix
_last_sent: dict[int, float] = {}

# Hard floor — no group may receive azkar faster than this
_MIN_INTERVAL_SEC = 300   # 5 minutes


def _get_interval_seconds() -> int:
    """يقرأ azkar_interval_minutes من bot_constants. الافتراضي 10 دقائق."""
    try:
        from core.admin import get_const_int
        return max(_MIN_INTERVAL_SEC, get_const_int("azkar_interval_minutes", 10) * 60)
    except Exception:
        return 600


def send_periodic_azkar():
    """
    يُرسَل من المُجدوِل كل 5 دقائق.
    يرسل ذكراً لكل مجموعة فعّلت azkar_enabled مع احترام الفترة الزمنية لكل مجموعة.
    الحد الأدنى للفترة: 5 دقائق (300 ثانية) — لا يمكن تجاوزه.

    NOTE: General azkar (azkar_content) are NEVER pinned.
    Only the four scheduled categories (morning/evening/sleep/wakeup) pin.
    """
    now = time.time()

    try:
        group_ids = get_all_group_ids()
    except Exception:
        return

    for tg_group_id in group_ids:
        try:
            enabled = get_group_setting(tg_group_id, "azkar_enabled")
            if not enabled:
                continue

            # فترة الإرسال الخاصة بالمجموعة (بالدقائق)، افتراضي 15
            # الحد الأدنى: 5 دقائق
            interval_min = get_group_setting(tg_group_id, "azkar_interval") or 15
            interval_sec = max(_MIN_INTERVAL_SEC, int(interval_min) * 60)

            if now - _last_sent.get(tg_group_id, 0) < interval_sec:
                continue

            row = get_random_azkar_content()
            if not row:
                continue

            bot.send_message(
                tg_group_id,
                f"📿<b>\n\n{row['content']}</b>",
                parse_mode="HTML",
            )
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

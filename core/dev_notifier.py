"""
core/dev_notifier.py
─────────────────────
Safe sender for the developer group.

Prevents bot crashes on:
  - 400: chat not found
  - 403: bot was kicked
  - Invalid group ID (-1)

All functions are no-op safe — they never raise exceptions.
"""
import logging
from typing import Optional

log = logging.getLogger("DevNotifier")


def _get_group_id() -> Optional[int]:
    """Fetches the dev group ID from bot_constants dynamically."""
    try:
        from core.admin import get_const_int
        gid = get_const_int("dev_group_id", -1)
        return gid if gid != -1 else None
    except Exception:
        return None


def send_to_dev_group(
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
    **kwargs,
) -> Optional[int]:
    """
    Sends a message to the dev group safely.
    Returns message_id on success, None on failure.
    Never raises.
    """
    gid = _get_group_id()
    if gid is None:
        log.debug("dev_group_id not set — skipping dev group message.")
        return None

    try:
        from core.bot import bot
        sent = bot.send_message(
            gid, text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs,
        )
        return sent.message_id
    except Exception as e:
        err = str(e)
        if any(x in err for x in ("chat not found", "bot was kicked", "400", "403")):
            log.warning(f"[DevNotifier] Cannot reach dev group {gid}: {e}")
            _notify_primary_dev_on_failure(gid, err)
        else:
            log.error(f"[DevNotifier] Unexpected error sending to dev group: {e}")
        return None


def edit_dev_group_message(
    message_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> bool:
    """
    Edits a message in the dev group safely.
    Returns True on success.
    """
    gid = _get_group_id()
    if gid is None:
        return False

    try:
        from core.bot import bot
        bot.edit_message_text(
            text, gid, message_id,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except Exception as e:
        log.warning(f"[DevNotifier] Cannot edit dev group message: {e}")
        return False


def _notify_primary_dev_on_failure(group_id: int, error: str) -> None:
    """
    Notifies the primary developer via PM if the group is unreachable.
    Called at most once per error type (throttled by caller).
    """
    try:
        from core.config import developers_id
        from core.bot import bot
        primary = next(iter(developers_id), None)
        if not primary:
            return
        bot.send_message(
            primary,
            f"⚠️ <b>تحذير: مجموعة المطورين غير متاحة</b>\n\n"
            f"المعرف: <code>{group_id}</code>\n"
            f"الخطأ: <code>{error[:200]}</code>\n\n"
            f"تحقق من أن البوت لا يزال عضواً في المجموعة.",
            parse_mode="HTML",
        )
    except Exception:
        pass

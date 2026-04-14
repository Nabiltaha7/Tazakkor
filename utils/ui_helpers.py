"""
utils/ui_helpers.py
────────────────────
Pagination-aware UI helpers for developer panel flows.

These functions work with the pagination button system (utils/pagination)
and support edit-or-send semantics needed by multi-step flows.

Key distinction from utils/bot_helpers.py:
  - bot_helpers.send_result()  → simple send, no edit, no pagination buttons
  - ui_helpers.send_or_edit()  → tries edit first, falls back to send,
                                  supports pagination buttons + owner checks
"""
from core.bot import bot
from utils.pagination import btn
from utils.pagination.buttons import build_keyboard

_B = "p"   # primary (blue)
_R = "d"   # danger  (red)


def send_or_edit(
    chat_id: int,
    text: str,
    message_id: int = None,
    buttons: list = None,
    layout: list = None,
    owner_id: int = None,
    parse_mode: str = "HTML",
) -> int | None:
    """
    Displays a result panel:
    - If message_id is given → tries to edit the message in place
    - If edit fails or no message_id → sends a new message
    - Returns the actual message_id of the sent/edited message

    Default buttons (when buttons=None and owner_id is given):
      ⬅️ رجوع (dev_back_main)  +  ❌ إغلاق (dev_close)
    """
    if buttons is None and owner_id is not None:
        owner   = (owner_id, chat_id)
        buttons = [
            btn("⬅️ رجوع", "dev_back_main", {}, color=_B, owner=owner),
            btn("❌ إغلاق", "dev_close",     {}, color=_R, owner=owner),
        ]
        layout = layout or [2]

    markup = build_keyboard(buttons, layout or [1], owner_id) if buttons else None

    if message_id:
        try:
            bot.edit_message_text(
                text, chat_id, message_id,
                parse_mode=parse_mode,
                reply_markup=markup,
            )
            return message_id
        except Exception:
            pass  # fallback to send

    try:
        sent = bot.send_message(
            chat_id, text,
            parse_mode=parse_mode,
            reply_markup=markup,
        )
        return sent.message_id
    except Exception:
        return None


def cancel_buttons(
    owner: tuple,
    back_action: str = "dev_back_main",
) -> tuple[list, list]:
    """Returns (buttons, layout) for a standard back + close button pair."""
    return [
        btn("⬅️ رجوع", back_action, {}, color=_B, owner=owner),
        btn("❌ إغلاق", "dev_close",  {}, color=_R, owner=owner),
    ], [2]


def prompt_with_cancel(
    chat_id: int,
    uid: int,
    text: str,
    message_id: int = None,
    cancel_action: str = "hub_dev_cancel",
) -> int | None:
    """
    Displays an input-prompt message with a single cancel button.
    Returns the actual message_id.
    """
    owner      = (uid, chat_id)
    cancel_btn = btn("🚫 إلغاء", cancel_action, {}, color=_R, owner=owner)
    markup     = build_keyboard([cancel_btn], [1], uid)

    if message_id:
        try:
            bot.edit_message_text(
                text, chat_id, message_id,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return message_id
        except Exception:
            pass

    try:
        sent = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        return sent.message_id
    except Exception:
        return None

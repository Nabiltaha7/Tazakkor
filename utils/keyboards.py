"""
utils/keyboards.py
───────────────────
Simple inline keyboard builders using direct callback_data (no cache).

Use this for URL buttons and simple callback buttons that don't need
owner-checking or the pagination cache system.

For paginated panels with owner checks, use utils/pagination instead.
"""
import json

from telebot import types
from core.bot import bot


# ══════════════════════════════════════════
# Button builder
# ══════════════════════════════════════════

def ui_btn(text: str, action: str = None, data: dict = None,
           url: str = None, style: str = "primary") -> types.InlineKeyboardButton:
    """
    Builds a single InlineKeyboardButton.

    Args:
        text:   Button label.
        action: Callback action identifier (used as callback_data key "a").
        data:   Extra dict merged into callback_data payload.
        url:    External URL (mutually exclusive with action).
        style:  Button color — "primary", "success", "danger", "secondary", "default".
    """
    if url:
        kwargs = {"text": text, "url": url}
        if style != "default":
            kwargs["style"] = style
        return types.InlineKeyboardButton(**kwargs)

    payload       = {"a": action}
    if data:
        payload.update(data)
    callback_data = json.dumps(payload, separators=(",", ":"))

    kwargs = {"text": text, "callback_data": callback_data}
    if style != "default":
        kwargs["style"] = style
    return types.InlineKeyboardButton(**kwargs)


# ══════════════════════════════════════════
# Keyboard builder
# ══════════════════════════════════════════

def build_keyboard(
    buttons: list[types.InlineKeyboardButton],
    layout: list[int],
) -> types.InlineKeyboardMarkup:
    """
    Arranges buttons into rows according to layout.

    Args:
        buttons: Flat list of InlineKeyboardButton objects.
        layout:  Number of buttons per row, e.g. [2, 2, 1].

    Example:
        build_keyboard([b1, b2, b3, b4, b5], [2, 2, 1])
        → row1: b1 b2 | row2: b3 b4 | row3: b5
    """
    markup = types.InlineKeyboardMarkup()
    index  = 0
    for count in layout:
        row = []
        for _ in range(count):
            if index >= len(buttons):
                break
            row.append(buttons[index])
            index += 1
        if row:
            markup.row(*row)
    return markup


# ══════════════════════════════════════════
# Simple send / edit helpers
# ══════════════════════════════════════════

def send_ui(
    chat_id: int,
    text: str = None,
    photo=None,
    buttons: list = None,
    layout: list = None,
):
    """
    Sends a message or photo with an optional keyboard.
    For paginated panels with owner checks, use utils.pagination.send_ui instead.
    """
    markup = build_keyboard(buttons, layout or [1]) if buttons else None

    if photo:
        return bot.send_photo(
            chat_id, photo,
            caption=text,
            reply_markup=markup,
            parse_mode="HTML",
        )
    return bot.send_message(
        chat_id, text,
        reply_markup=markup,
        parse_mode="HTML",
    )


def edit_ui(
    call,
    text: str = None,
    buttons: list = None,
    layout: list = None,
) -> None:
    """
    Edits the message that triggered a callback.
    For paginated panels with owner checks, use utils.pagination.edit_ui instead.
    """
    markup = build_keyboard(buttons, layout or [1]) if buttons else None
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
        )
    except Exception:
        pass

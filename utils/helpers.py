"""
utils/helpers.py
─────────────────
Pure text/message helpers + backward-compatible re-exports from bot_helpers.

Rules:
  - Pure functions (no bot calls) live here.
  - Bot-dependent functions live in utils/bot_helpers.py.
  - Re-exports below keep all existing imports working without changes.
"""
import random

from .constants import (
    section_dividers, bullets, loading_bar, twinkle_line,
    vertical_separator, ayah_divider, post_divider,
    happy_cheer, lines, left_arrows, right_arrows,
    success_icons, error_icons, waiting_icon, warning_icon,
    next_icon, prev_icon,
)

# ── Backward-compatible re-exports from bot_helpers ──────────────────────────
from utils.bot_helpers import (
    get_bot_username,
    get_bot_photo_id,
    get_entity_photo_id,
    get_bot_link,
    make_open_bot_button,
    send_bot_profile,
    send_private_access_panel,
    safe_send_message,
    safe_reply,
    send_result,
    edit_result,
    can_contact_user,
    typing_delay,
    send_with_delay,
    send_with_delay_async,
)


# ══════════════════════════════════════════
# Shape / decorator helpers
# ══════════════════════════════════════════

def get_section_dividers() -> str:
    return random.choice(section_dividers)

def get_bullet() -> str:
    return random.choice(bullets)

def get_loading_bar() -> str:
    return loading_bar

def get_twinkle_line() -> str:
    return twinkle_line

def get_vertical_separator() -> str:
    return vertical_separator

def get_post_divider() -> str:
    return post_divider

def get_happy_cheer() -> str:
    return random.choice(happy_cheer)

def get_lines() -> str:
    return random.choice(lines)

def get_left_arrows() -> str:
    return random.choice(left_arrows)

def get_right_arrows() -> str:
    return random.choice(right_arrows)

def get_success_icons() -> str:
    return random.choice(success_icons)

def get_error_icons() -> str:
    return random.choice(error_icons)

def get_waiting_icon() -> str:
    return random.choice(waiting_icon)

def get_warning_icon() -> str:
    return random.choice(warning_icon)

def get_next_icon() -> str:
    return random.choice(next_icon)

def get_prev_icon() -> str:
    return random.choice(prev_icon)


# ══════════════════════════════════════════
# Chat type checks
# ══════════════════════════════════════════

def is_group(msg) -> bool:
    return msg.chat.type in ("group", "supergroup")

def is_private(msg) -> bool:
    return msg.chat.type == "private"


# ══════════════════════════════════════════
# Text helpers
# ══════════════════════════════════════════

def normalize_command_text(text: str) -> str:
    """
    Removes bot name prefix from command text if present.
    
    Examples:
        "تذكره مساعدة" → "مساعدة"
        "مساعدة" → "مساعدة"
        "تذكره ختمتي" → "ختمتي"
        "ختمتي" → "ختمتي"
    
    Returns:
        The command text with bot name prefix removed and trimmed.
    """
    from core.config import BOT_NAME
    
    if not text:
        return text
    
    text = text.strip()
    
    # Check if text starts with bot name (case-insensitive for Arabic)
    if text.startswith(BOT_NAME):
        # Remove bot name and trim any remaining spaces
        text = text[len(BOT_NAME):].strip()
    
    return text


def limit_text(text, max_length: int = 20, suffix: str = "...") -> str:
    """Truncates text to max_length characters."""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + suffix


def format_remaining_time(seconds: int) -> str:
    """Formats seconds into a human-readable Arabic duration string."""
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days > 0:
        parts.append("1 يوم" if days == 1 else f"{days} أيام")
    if hours > 0:
        if hours == 1:   parts.append("1 ساعة")
        elif hours == 2: parts.append("ساعتان")
        elif 3 <= hours <= 10: parts.append(f"{hours} ساعات")
        else: parts.append(f"{hours} ساعة")
    if minutes > 0:
        if minutes == 1:   parts.append("1 دقيقة")
        elif minutes == 2: parts.append("دقيقتان")
        elif 3 <= minutes <= 10: parts.append(f"{minutes} دقائق")
        else: parts.append(f"{minutes} دقيقة")
    if sec > 0:
        parts.append("1 ثانية" if sec == 1 else f"{sec} ثانية")
    elif not parts:
        parts.append("0 ثانية")

    return " و ".join(parts)


def convert_to_arabic_numbers(number) -> str:
    return str(number).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def format_ayah_number(ayah_number: int) -> str:
    reversed_number = str(ayah_number)[::-1]
    arabic_number   = convert_to_arabic_numbers(reversed_number)
    return f"{arabic_number}{ayah_divider}"


def safe_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def dont_have_power() -> str:
    return "<b>ليس لديك صلاحية لاستخدام هذا الأمر</b>"


# ══════════════════════════════════════════
# Legacy send helpers (bot-dependent, kept for backward compat)
# ══════════════════════════════════════════

def send_error(fun_name: str, error) -> str:
    return f"Error in {fun_name} : \n<b>{str(error)}</b>"


def send_error_reply(msg, text: str) -> None:
    from core.bot import bot
    try:
        bot.reply_to(msg, f"{get_error_icons()} {text}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(msg, send_error("send_error_reply", e), parse_mode="HTML")


def send_reply(msg, text: str, parse_html: bool = True, buttons=None, Shape: bool = True) -> None:
    from core.bot import bot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    try:
        markup = None
        if buttons:
            markup = InlineKeyboardMarkup()
            for row in buttons:
                markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])

        prefix     = get_section_dividers() if Shape else ""
        final_text = prefix + f"<b>{text}</b>"

        bot.reply_to(
            msg,
            final_text,
            parse_mode="HTML" if parse_html else None,
            reply_markup=markup,
        )
    except Exception as e:
        try:
            from core.bot import bot as _bot
            _bot.reply_to(msg, f"{str(e)} {get_error_icons()}", parse_mode="HTML")
        except Exception:
            pass


def send_message(chat_id: int, text: str, parse_html: bool = True,
                 buttons=None, reply_to_id: int = None) -> None:
    """Sends a new message. Use send_reply for normal replies."""
    from core.bot import bot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    try:
        markup = None
        if buttons:
            markup = InlineKeyboardMarkup()
            for row in buttons:
                markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])

        kwargs = {"parse_mode": "HTML" if parse_html else None, "reply_markup": markup}
        if reply_to_id:
            kwargs["reply_to_message_id"] = reply_to_id

        bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"[send_message] error: {e}")


def build_colored_buttons(buttons_data: list, cols: int = 1):
    """Builds an InlineKeyboardMarkup from a list of button dicts."""
    from utils.keyboards import ui_btn, build_keyboard as _kb
    btns = []
    for b in buttons_data:
        if b.get("url"):
            btns.append(ui_btn(b["label"], url=b["url"], style=b.get("style", "primary")))
        elif b.get("cb"):
            btns.append(ui_btn(b["label"], action=b["cb"], style=b.get("style", "primary")))
    if not btns:
        return None
    layout = []
    rem    = len(btns)
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return _kb(btns, layout)


def get_target_user_id(message, text: str = None):
    """Delegates to utils.user_resolver — single source of truth."""
    from utils.user_resolver import get_target_user_id as _resolve
    return _resolve(message, text)

"""
utils/bot_helpers.py
─────────────────────
Bot-specific helpers: profile photos, PM buttons, safe send/edit.

These functions depend on the bot instance and make Telegram API calls.
Pure text/formatting helpers live in utils/helpers.py.
"""
import threading
import time
from typing import Optional

from core.bot import bot
from core.config import bot_name
from telebot import types


# ══════════════════════════════════════════
# Bot identity
# ══════════════════════════════════════════

def get_bot_username() -> str:
    """Returns the bot's @username, cached after first call."""
    try:
        import core.bot as _cb
        if not getattr(_cb, "bot_username", None):
            _cb.bot_username = bot.get_me().username
        return _cb.bot_username or ""
    except Exception:
        return ""


def get_bot_photo_id() -> Optional[str]:
    """Returns the bot's latest profile photo file_id, cached. None if no photo."""
    try:
        import core.bot as _cb
        if not getattr(_cb, "_bot_photo_id", None):
            bot_id = bot.get_me().id
            photos = bot.get_user_profile_photos(bot_id, limit=1)
            _cb._bot_photo_id = photos.photos[0][-1].file_id if photos.total_count > 0 else ""
        return _cb._bot_photo_id or None
    except Exception:
        return None


def get_entity_photo_id(chat_id: int):
    """
    Returns a profile photo for any entity (group, user, bot).
    - Groups/channels: downloads and returns bytes (big_file_id can't be used directly)
    - Users/bots: returns file_id string
    Returns None if no photo or download fails.
    """
    try:
        chat = bot.get_chat(chat_id)
        if chat.type in ("group", "supergroup", "channel"):
            photo = getattr(chat, "photo", None)
            if not photo:
                return None
            file_info = bot.get_file(photo.big_file_id)
            return bot.download_file(file_info.file_path)
        photos = bot.get_user_profile_photos(chat_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][-1].file_id
        return None
    except Exception:
        return None


def get_bot_link() -> str:
    """Returns an HTML link to the bot."""
    username = get_bot_username()
    return f'<a href="https://t.me/{username}">{bot_name}</a>' if username else f"<b>{bot_name}</b>"


# ══════════════════════════════════════════
# PM / profile send helpers
# ══════════════════════════════════════════

def make_open_bot_button() -> types.InlineKeyboardMarkup:
    """Builds a URL button to open the bot's PM."""
    username = get_bot_username()
    markup = types.InlineKeyboardMarkup()
    if username:
        markup.add(types.InlineKeyboardButton(
            "🔓 فتح خاص البوت",
            url=f"https://t.me/{username}",
        ))
    return markup


def send_bot_profile(
    chat_id: int,
    caption: str,
    reply_to: int = None,
    open_pm_button: bool = False,
) -> None:
    """Sends the bot's current profile photo with a caption. Falls back to text."""
    markup = None
    if open_pm_button:
        username = get_bot_username()
        if username:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "💬 فتح خاص البوت",
                url=f"https://t.me/{username}",
            ))

    photo_id = get_bot_photo_id()
    kwargs = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(
                chat_id, caption,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=markup,
                reply_to_message_id=reply_to,
            )
    except Exception as e:
        print(f"[send_bot_profile] error: {e}")


def send_private_access_panel(
    chat_id: int,
    caption: str = None,
    reply_to: int = None,
    extra_buttons: list = None,
) -> None:
    """Sends the bot's profile photo with a PM button and optional extra buttons."""
    from utils.keyboards import ui_btn, build_keyboard

    username = get_bot_username()
    if caption is None:
        caption = (
            "💬 <b>افتح خاص البوت</b>\n\n"
            "لاستخدام هذه الميزة يجب أن تبدأ محادثة خاصة مع البوت أولاً.\n"
            "اضغط الزر بالأسفل ثم اضغط <b>Start</b>."
        )

    buttons = []
    if username:
        buttons.append(ui_btn(f"💬 {bot_name}", url=f"https://t.me/{username}", style="primary"))
    if extra_buttons:
        buttons.extend(extra_buttons)

    cols   = min(len(buttons), 2)
    layout = []
    rem    = len(buttons)
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols

    markup   = build_keyboard(buttons, layout) if buttons else None
    photo_id = get_bot_photo_id()
    kwargs   = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(
                chat_id, caption,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=markup,
                reply_to_message_id=reply_to,
            )
    except Exception as e:
        print(f"[send_private_access_panel] error: {e}")


# ══════════════════════════════════════════
# Safe send / edit
# ══════════════════════════════════════════

def safe_send_message(
    chat_id: int,
    text: str,
    reply_to_id: int = None,
    markup=None,
    parse_mode: str = "HTML",
) -> Optional[object]:
    """
    Sends a message with automatic fallback:
    1. Tries with reply_to_message_id
    2. If 'message to be replied not found' → retries without reply
    3. On total failure → logs and returns None
    """
    kwargs = {
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
        "reply_markup": markup,
    }
    if reply_to_id:
        kwargs["reply_to_message_id"] = reply_to_id

    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        err = str(e).lower()
        if reply_to_id and "message to be replied not found" in err:
            kwargs.pop("reply_to_message_id", None)
            try:
                return bot.send_message(chat_id, text, **kwargs)
            except Exception as e2:
                print(f"[safe_send_message] retry failed cid={chat_id}: {e2}")
                return None
        print(f"[safe_send_message] failed cid={chat_id}: {e}")
        return None


def safe_reply(message, text: str, parse_mode: str = "HTML", markup=None) -> Optional[object]:
    """Safe bot.reply_to — falls back to plain send if original message was deleted."""
    return safe_send_message(
        chat_id=message.chat.id,
        text=text,
        reply_to_id=message.message_id,
        markup=markup,
        parse_mode=parse_mode,
    )


def send_result(chat_id: int, text: str, buttons=None, reply_to_id: int = None) -> None:
    """Standard message send: HTML, no preview, with optional inline buttons."""
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = None
    if buttons:
        markup = InlineKeyboardMarkup()
        for row in buttons:
            markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])
    safe_send_message(chat_id, text, reply_to_id=reply_to_id, markup=markup)


def edit_result(chat_id: int, message_id: int, text: str, buttons=None) -> None:
    """Standard message edit: HTML, no preview, with optional inline buttons."""
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = None
    if buttons:
        markup = InlineKeyboardMarkup()
        for row in buttons:
            markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])
    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup,
        )
    except Exception as e:
        print(f"[edit_result] error: {e}")


def can_contact_user(user_id: int) -> bool:
    """Returns True if the user has started a PM with the bot and hasn't blocked it."""
    try:
        bot.send_chat_action(user_id, "typing")
        return True
    except Exception:
        return False


# ══════════════════════════════════════════
# Typing delay helpers
# ══════════════════════════════════════════

def typing_delay(chat_id: int, delay: float = 0.6) -> None:
    """Sends 'typing...' action then waits delay seconds."""
    try:
        bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass
    time.sleep(max(0.3, min(delay, 1.5)))


def send_with_delay(
    chat_id: int,
    text: str,
    delay: float = 0.6,
    parse_mode: str = "HTML",
    reply_to: int = None,
    markup=None,
) -> Optional[object]:
    """Sends a message after a realistic typing delay."""
    typing_delay(chat_id, delay)
    kwargs = {"parse_mode": parse_mode}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    if markup:
        kwargs["reply_markup"] = markup
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"[send_with_delay] error: {e}")
        return None


def send_with_delay_async(
    chat_id: int,
    text: str,
    delay: float = 0.6,
    parse_mode: str = "HTML",
    reply_to: int = None,
    markup=None,
) -> None:
    """Non-blocking version of send_with_delay."""
    def _run():
        send_with_delay(chat_id, text, delay, parse_mode, reply_to, markup)
    threading.Thread(target=_run, daemon=True).start()

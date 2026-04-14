"""
handlers/chat_responses/chat_handler.py
────────────────────────────────────────
Automatic chat response dispatcher.
"""
import random

from core.bot import bot
from .chat_responses import salam_responses, prophet_responses
from .chat_triggers import SALAM_WORDS


def _send_random(message, responses: list) -> None:
    """Replies with a random item from the responses list."""
    bot.reply_to(message, "<b>" + random.choice(responses) + "</b>", parse_mode="HTML")


def chat_responses(message) -> None:
    """Checks message text and sends an automatic response if triggered."""
    if not message.text:
        return

    text = message.text.strip().lower()

    if text.startswith(tuple(SALAM_WORDS)):
        _send_random(message, salam_responses)
    elif "النبي" in text or "الرسول" in text:
        _send_random(message, prophet_responses)

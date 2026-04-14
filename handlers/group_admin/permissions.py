"""
handlers/group_admin/permissions.py
─────────────────────────────────────
Permission checks for group admin commands.

Rules:
  - is_developer() → delegates to core.admin (single source of truth)
  - sender_can_*() → checks the command sender's permissions
  - bot_is_admin() / can_*() → checks the bot's own permissions
"""
from core.bot import bot
from core.admin import is_any_dev


def is_developer(message) -> bool:
    """Returns True if the message sender is a bot developer."""
    return is_any_dev(message.from_user.id)


def is_admin(message) -> bool:
    """Returns True if the message sender is a group admin or creator."""
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def get_sender_member(message):
    """Returns the ChatMember object for the message sender, or None."""
    try:
        return bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        return None


def get_bot_member(chat_id):
    """Returns the bot's ChatMember object, or None."""
    try:
        return bot.get_chat_member(chat_id, bot.get_me().id)
    except Exception:
        return None


# ── Sender-level permission checks ───────────────────────────────────────────

def sender_can_delete(message) -> tuple[bool, str]:
    """Returns (True, "") if the sender may delete messages."""
    member = get_sender_member(message)
    if not member:
        return False, "❌ تعذّر التحقق من صلاحياتك."
    if member.status == "creator":
        return True, ""
    if member.status != "administrator":
        return False, "❌ أنت لست مشرفاً في هذه المجموعة."
    if not member.can_delete_messages:
        return False, "⛔ ليس لديك صلاحية <b>حذف الرسائل</b>."
    return True, ""


def sender_can_pin(message) -> tuple[bool, str]:
    """Returns (True, "") if the sender may pin messages."""
    member = get_sender_member(message)
    if not member:
        return False, "❌ تعذّر التحقق من صلاحياتك."
    if member.status == "creator":
        return True, ""
    if member.status != "administrator":
        return False, "❌ أنت لست مشرفاً في هذه المجموعة."
    if not member.can_pin_messages:
        return False, "⛔ ليس لديك صلاحية <b>تثبيت الرسائل</b>."
    return True, ""


# ── Bot-level permission checks ───────────────────────────────────────────────

def bot_is_admin(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return m is not None and m.status == "administrator"


def can_delete_messages(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_delete_messages)


def can_pin_messages(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_pin_messages)

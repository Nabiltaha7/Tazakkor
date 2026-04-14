"""
handlers/group_admin/admin_commands.py
───────────────────────────────────────
Group admin commands: delete, pin, and developer DB tools.
"""
from core.admin import is_any_dev
from core.bot import bot
from handlers.group_admin.permissions import (
    sender_can_delete, sender_can_pin,
    can_delete_messages, can_pin_messages,
)


def _reply(message, text: str) -> None:
    bot.reply_to(message, text, parse_mode="HTML", disable_web_page_preview=True)


def delete_message(message) -> None:
    ok, err = sender_can_delete(message)
    if not ok:
        _reply(message, err)
        return

    if not can_delete_messages(message.chat.id):
        _reply(message, "⛔ البوت لا يملك صلاحية <b>حذف الرسائل</b>.")
        return

    if not message.reply_to_message:
        _reply(message, "يجب الرد على الرسالة المراد حذفها.")
        return

    try:
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)
    except Exception as e:
        _reply(message, f"فشل الحذف: {e}")


def pin_message(message) -> None:
    ok, err = sender_can_pin(message)
    if not ok:
        _reply(message, err)
        return

    if not can_pin_messages(message.chat.id):
        _reply(message, "⛔ البوت لا يملك صلاحية <b>تثبيت الرسائل</b>.")
        return

    if not message.reply_to_message:
        _reply(message, "يجب الرد على الرسالة المراد تثبيتها.")
        return

    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        _reply(message, "📌 تم تثبيت الرسالة.")
    except Exception as e:
        _reply(message, f"فشل التثبيت: {e}")


def update_db(message) -> None:
    """Runs DB migrations — developer only."""
    if not is_any_dev(message.from_user.id):
        return
    try:
        from database.update_db import update_database
        update_database()
        _reply(message, "✅ تم تحديث قاعدة البيانات بنجاح.")
    except Exception as e:
        _reply(message, f"خطأ أثناء التحديث: {e}")

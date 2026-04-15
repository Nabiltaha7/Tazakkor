"""
handlers/command_handlers/group_commands.py
────────────────────────────────────────────
Group-only commands.
"""
from core.bot import bot
from core.admin import is_any_dev


def handle_group_commands(message, normalized_text: str, text: str) -> bool:
    """
    Handles group-only commands.
    Returns True if the command was handled.
    """
    uid = message.from_user.id
    cid = message.chat.id

    # ── Group settings panel (admins only) ──
    from handlers.group_admin.group_commands_panel import open_commands_panel
    if open_commands_panel(message):
        return True

    # ── Group invite link ──
    if normalized_text in ("الرابط", "رابط القروب"):
        _send_group_link(message)
        return True

    # ── Developer-only commands ──
    if is_any_dev(uid):
        if normalized_text in ("تحديث جروب البوت", "تعيين جروب البوت"):
            _set_dev_group(message)
            return True

        if normalized_text in ("إدارة الأذكار", "ادارة الأذكار", "azkar admin"):
            from modules.azkar.azkar_handler import open_azkar_admin
            open_azkar_admin(message)
            return True

        if normalized_text == "تحديث قاعدة البيانات":
            from handlers.group_admin.admin_commands import update_db
            update_db(message)
            return True

    # ── Features guide ──
    from handlers.features_guide import handle_features_command
    if handle_features_command(message):
        return True

    return False


def _send_group_link(message) -> None:
    """Sends the group's invite link with requester info."""
    from utils.keyboards import ui_btn, build_keyboard

    cid        = message.chat.id
    uid        = message.from_user.id
    first_name = message.from_user.first_name or ""
    group_name = message.chat.title or "المجموعة"

    try:
        invite_link = bot.export_chat_invite_link(cid)
    except Exception:
        invite_link = None

    sender_line = f"<a href='tg://user?id={uid}'>{first_name}</a> (<code>{uid}</code>)"

    if invite_link:
        text   = (
            f"🔗 <b>رابط المجموعة</b>\n\n"
            f"👤 الطالب: {sender_line}\n"
            f"👥 المجموعة: <b>{group_name}</b>\n\n"
            f"<code>{invite_link}</code>"
        )
        markup = build_keyboard([ui_btn("🔗 رابط المجموعة", url=invite_link)], [1])
    else:
        text = (
            f"⚠️ تعذّر جلب رابط المجموعة.\n\n"
            f"👤 الطالب: {sender_line}\n"
            f"👥 المجموعة: <b>{group_name}</b>\n\n"
            f"تأكد أن البوت يملك صلاحية <b>دعوة المستخدمين</b>."
        )
        markup = None

    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)


def _set_dev_group(message) -> None:
    """Sets this group as the bot's developer group."""
    from core.admin import set_const
    group_id = str(message.chat.id)
    set_const("dev_group_id", group_id)
    try:
        import modules.tickets.ticket_handler as _th
        _th.DEV_GROUP_ID = int(group_id)
    except Exception:
        pass
    bot.reply_to(
        message,
        f"✅ تم تعيين هذه المجموعة كجروب البوت الرئيسي\nID: <code>{group_id}</code>",
        parse_mode="HTML",
    )

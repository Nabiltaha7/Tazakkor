"""
handlers/command_handlers/shared_commands.py
─────────────────────────────────────────────
Commands that work in both groups and PM.
All module imports are lazy to avoid circular dependencies.
"""


def handle_shared_commands(message, normalized_text: str, text: str) -> bool:
    """
    Handles commands shared between groups and PM.
    Returns True if the command was handled.
    """
    # ── Tickets ──
    from modules.tickets.ticket_callbacks import handle_ticket_commands
    if handle_ticket_commands(message):
        return True

    # ── Quran ──
    from modules.quran.quran_handler import handle_quran_commands
    if handle_quran_commands(message):
        return True

    # ── Azkar ──
    from modules.azkar.azkar_handler import handle_azkar_command
    if handle_azkar_command(message):
        return True

    from modules.azkar.custom_zikr import handle_custom_zikr_command
    if handle_custom_zikr_command(message):
        return True

    from modules.azkar.azkar_reminder import handle_reminder_command
    if handle_reminder_command(message):
        return True

    # ── Admin panel ──
    if normalized_text in ("لوحة الإدارة", "لوحة الادارة", "لوحة المطور", "/admin"):
        from handlers.group_admin.developer.admin_panel import open_admin_panel
        open_admin_panel(message)
        return True

    if normalized_text in ("شرح المطور", "دليل المطور"):
        from handlers.group_admin.developer.dev_guide import open_dev_guide
        open_dev_guide(message)
        return True

    # ── Developer role commands ──
    from handlers.group_admin.developer.admin_panel import (
        handle_promote_dev_command, handle_demote_dev_command,
    )
    if handle_promote_dev_command(message): return True
    if handle_demote_dev_command(message):  return True

    return False

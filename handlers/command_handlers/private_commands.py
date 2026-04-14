"""
handlers/command_handlers/private_commands.py
──────────────────────────────────────────────
PM-only commands.
"""


def handle_private_commands(message) -> bool:
    """
    Handles PM-only commands.
    Returns True if the command was handled.
    """
    from modules.tickets.ticket_handler import handle_user_followup
    if handle_user_followup(message):
        return True

    return False

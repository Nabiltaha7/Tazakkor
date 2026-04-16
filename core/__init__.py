"""
core — Bot infrastructure layer

Exports the most commonly used core components for convenience.
"""
from .bot import bot
from .config import IS_TEST, developers_id, bot_name
from .state_manager import StateManager
from .admin import is_any_dev, is_primary_dev, is_secondary_dev
from .dev_notifier import send_to_dev_group, edit_dev_group_message

__all__ = [
    "bot",
    "IS_TEST", "developers_id", "bot_name",
    "StateManager",
    "is_any_dev", "is_primary_dev", "is_secondary_dev",
    "send_to_dev_group", "edit_dev_group_message",
]

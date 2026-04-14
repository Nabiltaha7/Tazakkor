"""
helpers/ui_helpers.py
──────────────────────
Backward-compatibility shim.

All functions have moved to utils/ui_helpers.py.
Import from there in new code:
    from utils.ui_helpers import send_or_edit, cancel_buttons, prompt_with_cancel
"""
from utils.ui_helpers import send_or_edit, cancel_buttons, prompt_with_cancel

# Legacy alias — old code that calls send_result() still works
send_result = send_or_edit

__all__ = ["send_result", "send_or_edit", "cancel_buttons", "prompt_with_cancel"]

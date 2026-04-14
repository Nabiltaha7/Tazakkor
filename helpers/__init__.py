"""
helpers/
─────────
Backward-compatibility shim. All UI helpers have moved to utils/ui_helpers.py.

New code should import directly:
    from utils.ui_helpers import send_or_edit, cancel_buttons, prompt_with_cancel
"""
from utils.ui_helpers import send_or_edit, cancel_buttons, prompt_with_cancel

# Legacy alias
send_result = send_or_edit

__all__ = ["send_result", "send_or_edit", "cancel_buttons", "prompt_with_cancel"]

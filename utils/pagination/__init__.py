"""
utils/pagination
─────────────────
Pagination system with owner-checked buttons and callback routing.

Public API:
  btn()             — builds a button dict for build_keyboard()
  build_keyboard()  — assembles buttons into an InlineKeyboardMarkup with cache
  send_ui()         — sends a message/photo with a paginated keyboard
  edit_ui()         — edits a message with a paginated keyboard
  register_action() — decorator to register a callback action handler
  paginate_list()   — slices a list into pages
  grid()            — builds a layout list for N items in C columns

State shims (backward-compat, delegate to StateManager):
  set_state()       — sets a state (old-style)
  get_state()       — gets a state (old-style)
  clear_state()     — clears a state
  is_busy()         — checks if a state exists
"""
from .buttons import btn, build_keyboard
from .router  import register_action, set_state, get_state, clear_state, is_busy, paginate_list
from .ui      import send_ui, edit_ui, grid

__all__ = [
    # buttons
    "btn",
    "build_keyboard",
    # router
    "register_action",
    "set_state",
    "get_state",
    "clear_state",
    "is_busy",
    "paginate_list",
    # ui
    "send_ui",
    "edit_ui",
    "grid",
]

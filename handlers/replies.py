"""
handlers/replies.py
────────────────────
Main message router — entry point for all incoming messages.

Flow:
  receive_responses()
    ├── Flow Engine (StateManager)   — highest priority
    ├── _public_commands()           — /start, deep links, المطور
    └── _dispatch() / _dispatch_private()
          ├── add_user_if_not_exists
          ├── _handle_input_states() — awaiting-input handlers
          ├── handle_shared_commands()
          ├── handle_group_commands()  (groups only)
          ├── handle_private_commands() (PM only)
          └── chat_responses()
"""
import traceback

from core.bot import bot
from core.state_manager import StateManager
from core.admin import is_any_dev
from utils.logger import log_event
from utils.bot_helpers import send_result

from handlers.chat_responses.chat_handler import chat_responses
from handlers.general.general_handler import show_developer
from handlers.users import add_user_if_not_exists, send_welcome


# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

def receive_responses(message) -> None:
    """Main entry point — mandatory error boundary."""
    if not message.from_user:
        return

    uid   = message.from_user.id
    cid   = message.chat.id
    state = StateManager.get(uid, cid)

    try:
        # Flow Engine — absolute priority (groups + PM)
        if StateManager.exists(uid, cid):
            from handlers.group_admin.developer.dev_flows import dispatch as _flow_dispatch
            if _flow_dispatch(message, uid, cid):
                return

        if _public_commands(message):
            return

        if _is_group(message):
            _dispatch(message)
        else:
            _dispatch_private(message)

    except Exception as e:
        _handle_error(uid, cid, e, state)


def _handle_error(uid: int, cid: int, exc: Exception, state) -> None:
    """Handles exceptions: silent for routine API errors, reported otherwise."""
    err_str = str(exc).lower()
    is_routine = any(x in err_str for x in (
        "message is not modified",
        "message to edit not found",
        "bot was blocked",
        "user is deactivated",
        "chat not found",
        "have no rights",
        "not enough rights",
        "connection aborted",
        "remote end closed connection",
        "remotedisconnected",
        "connectionerror",
        "connection error",
        "timed out",
        "read timed out",
    ))

    StateManager.clear(uid, cid)
    tb = traceback.format_exc()
    log_event("flow_error", user=uid, chat=cid, error=str(exc), state=state)

    if is_routine:
        return

    _report_error_to_devs(uid, cid, exc, tb)

    try:
        send_result(
            chat_id=cid,
            text=(
                f"❌ <b>حدث خطأ أثناء التنفيذ</b>\n\n"
                f"<code>{_safe_escape(str(exc))}</code>\n\n"
                f"<i>تم إبلاغ المطورين تلقائياً.</i>"
            ),
        )
    except Exception:
        pass


def _safe_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _report_error_to_devs(uid: int, cid: int, exc: Exception, tb: str) -> None:
    try:
        from core.dev_notifier import send_to_dev_group
        short_tb = tb[-3000:] if len(tb) > 3000 else tb
        send_to_dev_group(
            f"🔴 <b>خطأ في التنفيذ</b>\n\n"
            f"👤 المستخدم: <code>{uid}</code>\n"
            f"💬 المحادثة: <code>{cid}</code>\n\n"
            f"❌ <b>الخطأ:</b>\n<code>{_safe_escape(str(exc))}</code>\n\n"
            f"📋 <b>Traceback:</b>\n<pre>{_safe_escape(short_tb)}</pre>"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# Public commands (groups + PM)
# ══════════════════════════════════════════

def _public_commands(message) -> bool:
    text = message.text or ""
    
    # Normalize command text (remove bot name prefix if present)
    from utils.helpers import normalize_command_text
    text = normalize_command_text(text)

    if text == "/start":
        send_welcome(message)
        return True

    # Deep link: /start azkar_N — opens an azkar session directly
    if text.startswith("/start azkar_"):
        try:
            zikr_type = int(text.split("azkar_")[1])
            _cmd_map  = {0: "أذكار الصباح", 1: "أذكار المساء",
                         2: "أذكار النوم",  3: "أذكار الاستيقاظ"}
            cmd = _cmd_map.get(zikr_type)
            if cmd:
                message.text = cmd
                from handlers.command_handlers.shared_commands import handle_shared_commands
                handle_shared_commands(message, cmd.lower(), cmd)
        except Exception:
            send_welcome(message)
        return True

    if text == "المطور":
        show_developer(message)
        return True

    return False


# ══════════════════════════════════════════
# Group dispatcher
# ══════════════════════════════════════════

def _dispatch(message) -> None:
    add_user_if_not_exists(message)

    uid = message.from_user.id
    cid = message.chat.id

    # Clear any stale router state that StateManager doesn't know about
    from utils.pagination.router import get_state as _gs, clear_state as _cs
    if _gs(uid, cid).get("state") and not StateManager.get(uid, cid):
        _cs(uid, cid)

    if _handle_input_states(message):
        return

    if not message.text:
        return

    # Normalize command text (remove bot name prefix if present)
    from utils.helpers import normalize_command_text
    original_text   = message.text
    normalized_cmd  = normalize_command_text(message.text.strip())
    
    # Temporarily update message.text with normalized version for handlers
    message.text = normalized_cmd
    text            = normalized_cmd
    normalized_text = text.lower()

    try:
        from handlers.command_handlers.shared_commands import handle_shared_commands
        if handle_shared_commands(message, normalized_text, text):
            return

        from handlers.command_handlers.group_commands import handle_group_commands
        handle_group_commands(message, normalized_text, text)
    finally:
        # Restore original text
        message.text = original_text


# ══════════════════════════════════════════
# PM dispatcher
# ══════════════════════════════════════════

def _dispatch_private(message) -> None:
    add_user_if_not_exists(message)

    if _handle_input_states(message):
        return

    if not message.text:
        return

    # Normalize command text (remove bot name prefix if present)
    from utils.helpers import normalize_command_text
    original_text   = message.text
    normalized_cmd  = normalize_command_text(message.text.strip())
    
    # Temporarily update message.text with normalized version for handlers
    message.text = normalized_cmd
    text            = normalized_cmd
    normalized_text = text.lower()

    try:
        from handlers.command_handlers.shared_commands import handle_shared_commands
        if handle_shared_commands(message, normalized_text, text):
            return

        from handlers.command_handlers.private_commands import handle_private_commands
        if handle_private_commands(message):
            return

        chat_responses(message)
    finally:
        # Restore original text
        message.text = original_text


# ══════════════════════════════════════════
# Input state handlers
# ══════════════════════════════════════════

def _handle_input_states(message) -> bool:
    """Dispatches to all awaiting-input handlers. Returns True if handled."""
    from handlers.group_admin.developer.admin_panel import handle_admin_input
    from handlers.group_admin.developer.dev_control_panel import handle_developer_input
    from modules.quran.quran_handler import handle_dev_quran_input
    from modules.tickets.ticket_callbacks import handle_ticket_commands, handle_ticket_media

    uid = message.from_user.id
    cid = message.chat.id

    if handle_admin_input(message):     return True
    if handle_developer_input(message): return True
    if handle_dev_quran_input(message): return True

    from modules.azkar.azkar_handler import handle_azkar_input
    if handle_azkar_input(message):     return True

    from modules.azkar.custom_zikr import handle_custom_zikr_input
    if handle_custom_zikr_input(message): return True

    from modules.post_creator import handle_post_creator_input
    if handle_post_creator_input(message): return True

    # Ticket message input (text only, awaiting state)
    ts = StateManager.get(uid, cid)
    if ts and ts.get("type") == "ticket_flow" and ts.get("step") == "await_msg":
        from modules.tickets.ticket_handler import handle_ticket_message_input
        if handle_ticket_message_input(message): return True

    if handle_ticket_commands(message): return True
    if handle_ticket_media(message):    return True

    return False


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def _is_group(message) -> bool:
    return message.chat.type in ("group", "supergroup")

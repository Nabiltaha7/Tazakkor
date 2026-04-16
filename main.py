"""
main.py
────────
Bot entry point.

Startup sequence:
  1. sys.path setup (must be first)
  2. Logging config
  3. DB schema init (PostgreSQL / Supabase)
  4. Schema migrations
  5. Scheduler registration
  6. keep_alive (Flask health-check thread)
  7. Bot polling loop
"""
import sys
import os

# ── Path setup — must happen before any project imports ──────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import time
import traceback

from core.bot import bot
from core.config import IS_TEST
from telebot.apihelper import ApiTelegramException

from database.db_scheme import create_all_tables
from database.update_db import update_database
from handlers.replies import receive_responses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# ══════════════════════════════════════════
# Message handlers
# ══════════════════════════════════════════

@bot.message_handler(func=lambda message: True)
def text_handler(message):
    """Routes all text messages through the main dispatcher."""
    try:
        receive_responses(message)
    except Exception as e:
        print(f"[text_handler] {e}\n{traceback.format_exc()}")


@bot.message_handler(content_types=[
    "photo", "video", "audio", "voice",
    "video_note", "document", "sticker", "animation",
])
def media_handler(message):
    """Routes media messages to the general dispatcher."""
    try:
        receive_responses(message)
    except Exception as e:
        print(f"[media_handler] {e}\n{traceback.format_exc()}")


# ══════════════════════════════════════════
# Polling loop
# ══════════════════════════════════════════

def start_bot() -> None:
    """Starts infinity polling with automatic restart on errors."""
    while True:
        try:
            print("🚀 Starting bot polling...")
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=10,
                skip_pending=True,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "inline_query",
                    "my_chat_member",
                ],
            )
        except ApiTelegramException as e:
            print(f"[Telegram API Error] {e}")
            time.sleep(5)
        except Exception as e:
            print(f"[Unexpected Error] {e}\n{traceback.format_exc()}")
            print("🔁 Restarting in 5 seconds...")
            time.sleep(5)


# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

if __name__ == "__main__":
    # Environment banner already printed by config.py on import.
    if IS_TEST:
        print("🧪 TEST MODE active")

    # 1. Create all tables (PostgreSQL — no file creation needed)
    create_all_tables()

    # 2. Apply schema migrations (drops, renames, etc.)
    update_database()

    # 3. Register scheduler jobs
    from database.daily_tasks import run_daily_tasks
    run_daily_tasks()

    # 4. Start Flask keep-alive thread
    from web.app import keep_alive
    keep_alive()

    # 5. Start polling
    start_bot()

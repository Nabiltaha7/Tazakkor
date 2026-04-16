"""
handlers/general/general_handler.py
─────────────────────────────────────
General public commands (المطور).
"""
import random

from core.bot import bot
from core.config import developers_id
from utils.keyboards import ui_btn, send_ui
from utils.constants import lines, bullets, right_arrows, section_dividers


def show_developer(message) -> None:
    """Sends the developer info card with profile photo."""
    try:
        bot_user  = bot.get_me()
        bot_name  = bot_user.first_name

        bullet           = random.choice(bullets)
        arrow            = random.choice(right_arrows)
        section_divider  = random.choice(section_dividers)

        dev_id   = list(developers_id)[0]
        dev_user = bot.get_chat(dev_id)
        dev_name = f"{dev_user.first_name or ''} {dev_user.last_name or ''}".strip()
        dev_bio  = getattr(dev_user, "bio", "لا يوجد بايو")

        text = (
            f"{section_divider} Bot {arrow} <b>{bot_name}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{bullet} Dev {arrow} <a href='tg://user?id={dev_id}'><b>{dev_name}</b></a>\n"
            f"{bullet} Bio {arrow} <b>{dev_bio}</b>"
        )

        buttons = [
            ui_btn(text=dev_name, url=f"tg://user?id={dev_id}", style="success"),
            ui_btn(text=f"تحديثات {bot_name}", url="https://t.me/BotTazakkor", style="primary"),
        ]

        photos = bot.get_user_profile_photos(dev_id)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            send_ui(chat_id=message.chat.id, text=text,
                    photo=file_id, buttons=buttons, layout=[1, 1])
        else:
            send_ui(chat_id=message.chat.id, text=text,
                    buttons=buttons, layout=[1, 1])

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")

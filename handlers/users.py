"""
handlers/users.py
──────────────────
User registration and welcome message.
"""
from core.bot import bot
from utils.helpers import get_lines
from utils.bot_helpers import get_bot_username, get_bot_photo_id
from utils.keyboards import ui_btn, build_keyboard


def add_user_if_not_exists(msg) -> None:
    """Upserts the user in the database on every message."""
    user_id   = msg.from_user.id
    full_name = (msg.from_user.first_name or "") + (
        " " + msg.from_user.last_name if msg.from_user.last_name else ""
    )
    username = msg.from_user.username or None

    try:
        from database.db_queries.groups_queries import upsert_user_identity
        upsert_user_identity(user_id, full_name, username)
    except Exception as e:
        print(f"[add_user_if_not_exists] error: {e}")


def send_welcome(message) -> None:
    """Sends the bot's welcome message with profile photo."""
    caption = (
        f"<b>أهلاً وسهلاً! 👋</b>\n"
        f"{get_lines()}\n\n"
        f"أنا <b>تَذَكُّر | Tazakkor</b> — بوتك الإسلامي الشامل.\n\n"
        f"📿 <b>الأذكار:</b>\n"
        f"أذكار الصباح والمساء والنوم والاستيقاظ، ذكر مؤقت شخصي\n\n"
        f"📖 <b>القرآن الكريم:</b>\n"
        f"تلاوة يومية، ختمة القرآن، بحث في الآيات، تفسير\n\n"
        f"🔔 <b>التذكيرات:</b>\n"
        f"تذكيرات أذكار يومية، تذكير ختمة القرآن\n\n"
        f"⚙️ <b>إدارة المجموعات:</b>\n"
        f"إعدادات الأذكار التلقائية، ضبط التوقيت، تذاكر الدعم\n\n"
        f"{get_lines()}\n"
        f"أضفني مشرفاً في مجموعتك واكتب <code>الأوامر</code> لعرض الإعدادات\n"
        f"اكتب <code>مميزات</code> لاستعراض كل الميزات\n"
    )

    username = get_bot_username()
    buttons  = []

    
    if username:
        buttons.append(ui_btn("تَذَكُّر | Tazakkor",
                                url=f"https://t.me/{username}", style="success"))
        buttons.append(ui_btn("أضفني لمجموعتك",
                                url=f"https://t.me/{username}?startgroup=true",
                                style="primary"))

    markup   = build_keyboard(buttons, [1] * len(buttons)) if buttons else None
    photo_id = get_bot_photo_id()
    kwargs   = {
        "caption":             caption,
        "parse_mode":          "HTML",
        "reply_markup":        markup,
        "reply_to_message_id": message.message_id,
    }
    try:
        if photo_id:
            bot.send_photo(message.chat.id, photo_id, **kwargs, has_spoiler=True,)
        else:
            bot.send_message(message.chat.id, caption,
                             parse_mode="HTML", reply_markup=markup,
                             reply_to_message_id=message.message_id)
    except Exception as e:
        print(f"[send_welcome] error: {e}")

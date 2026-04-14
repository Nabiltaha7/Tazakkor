"""
نظام الترحيب والوداع — نسخة احترافية.
"""
from core.bot import bot
from core.config import bot_name, developers_id
from utils.helpers import get_bot_username, get_lines, get_bot_photo_id, get_entity_photo_id
from utils.keyboards import ui_btn, build_keyboard


_DEV_ID      = list(developers_id)[0] if developers_id else None
_UPDATES_URL = "https://t.me/BotTazakkor"

# ══════════════════════════════════════════
# البوت أُضيف لمجموعة
# ══════════════════════════════════════════

def _send_bot_joined(message):
    """Sent when the bot itself is added to a group."""
    cid        = message.chat.id
    group_name = message.chat.title or "المجموعة"

    # ── فحص صلاحيات البوت ──
    bot_id    = bot.get_me().id
    is_admin  = False
    try:
        member   = bot.get_chat_member(cid, bot_id)
        is_admin = member.status in ("administrator", "creator")
    except Exception:
        pass

    # جلب معلومات المجموعة الكاملة
    group_username = ""
    group_desc     = ""
    try:
        chat_info      = bot.get_chat(cid)
        group_username = f"@{chat_info.username}" if getattr(chat_info, "username", None) else ""
        group_desc     = getattr(chat_info, "description", None) or ""
    except Exception:
        pass

    # جلب اسم المالك
    owner_name = "غير معروف"
    try:
        admins = bot.get_chat_administrators(cid)
        owner  = next((a for a in admins if a.status == "creator"), None)
        if owner:
            owner_name = owner.user.first_name or owner_name
    except Exception:
        pass

    if is_admin:
        caption = (
            f"✅ <b>تم تفعيل بوت {bot_name} بنجاح!</b>\n"
            f"{get_lines()}\n\n"
            f"📛 اسم القروب: <b>{group_name}</b>\n"
        )
        if group_username:
            caption += f"🔗 يوزر القروب: {group_username}\n"
        caption += f"👑 المالك: <b>{owner_name}</b>\n"
        if group_desc:
            caption += f"📝 الوصف: {group_desc}\n"
        caption += f"\n✨ البوت الآن جاهز لإدارة القروب وتقديم المميزات"
    else:
        caption = (
            f"⚠️ <b>تم إضافة {bot_name} للمجموعة</b>\n"
            f"{get_lines()}\n\n"
            f"📛 المجموعة: <b>{group_name}</b>\n\n"
            f"❗ <b>البوت يحتاج صلاحيات المشرف ليعمل بشكل صحيح.</b>\n\n"
            f"يرجى ترقية البوت إلى مشرف حتى يتمكن من:\n"
            f"• إدارة الأعضاء (كتم، حظر، تقييد)\n"
            f"• إرسال رسائل الترحيب\n"
            f"• تثبيت الرسائل وإدارة المجموعة"
        )

    buttons = _build_bot_joined_buttons()

    photo_id = get_entity_photo_id(cid) or get_bot_photo_id()
    _send_photo_or_text(cid, photo_id, caption, buttons)


def _build_bot_joined_buttons():
    """Developer button + updates channel button."""
    buttons = []

    if _DEV_ID:
        try:
            dev_user = bot.get_chat(_DEV_ID)
            dev_name = dev_user.first_name or "المطور"
            if dev_user.username:
                buttons.append(ui_btn(
                    f"👨‍💻 {dev_name}",
                    url=f"https://t.me/{dev_user.username}",
                    style="success",
                ))
        except Exception:
            pass

    buttons.append(ui_btn("📢 قناة التحديثات", url=_UPDATES_URL, style="primary"))

    return build_keyboard(buttons, [1] * len(buttons)) if buttons else None

# ══════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════

def _build_welcome_markup(message):
    """Bot PM button + group owner button."""
    bot_username = get_bot_username()
    buttons = []

    if bot_username:
        buttons.append(ui_btn(bot_name, url=f"https://t.me/{bot_username}",
                               style="primary"))
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        owner  = next((a for a in admins if a.status == "creator"), None)
        if owner and owner.user.username:
            buttons.append(ui_btn(
                f"👑 {owner.user.first_name}",
                url=f"https://t.me/{owner.user.username}",
                style="danger",
            ))
    except Exception:
        pass

    return build_keyboard(buttons, [1] * len(buttons)) if buttons else None


def _send_photo_or_text(chat_id, photo_id, caption, markup, reply_to=None):
    """Send photo with caption using file_id, fallback to text if no photo."""
    kwargs = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML",
                             reply_markup=markup, reply_to_message_id=reply_to)
    except Exception as e:
        print(f"[welcome] error: {e}")

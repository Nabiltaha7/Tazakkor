# utils/pagination/buttons.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


_STYLE_MAP = {
    "p":  "primary",   # blue
    "su": "success",   # green
    "d":  "danger",    # red
    "de": "default",   # no color
}

def btn(text: str, action: str, data: dict = None, color: str = "p", owner: tuple = None):
    data = data or {}
    style = _STYLE_MAP.get(color, "primary")
    return {"text": text, "action": action, "data": data, "style": style, "owner": owner}

def build_keyboard(buttons: list, layout: list, owner_id: int):
    from .cache import store_cache
    markup = InlineKeyboardMarkup()
    index = 0
    for row_size in layout:
        row = []
        for _ in range(row_size):
            if index >= len(buttons):
                break
            b = buttons[index]
            # per-button owner takes priority; fall back to keyboard-level owner_id
            btn_owner = b.get("owner") or ((owner_id, None) if owner_id else None)
            uid = btn_owner[0] if btn_owner else None
            cid = btn_owner[1] if btn_owner else None
            payload = {
                "a": b.get("action"),
                "d": b.get("data", {}),
                "style": b.get("style"),
            }
            key = store_cache(uid, cid, payload, owner=btn_owner)
            if b.get("style") == "default":
                row.append(InlineKeyboardButton(
                text=b["text"],
                callback_data=f"k:{key}",
                ))
            else:
                row.append(InlineKeyboardButton(
                    text=b["text"],
                    callback_data=f"k:{key}",
                    style=b.get("style")
                ))
            index += 1
        if row:
            markup.row(*row)
    return markup
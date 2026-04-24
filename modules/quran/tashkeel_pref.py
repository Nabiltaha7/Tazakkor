"""
modules/quran/tashkeel_pref.py
────────────────────────────────
Global tashkeel (diacritics) preference system.

Command: "تشكيل الآيات"
  → Shows feature selector (ختمتي / قراءة سورة / آية)
  → Then shows format picker (بالتشكيل / بدون تشكيل)
  → Saves to user_quran_preferences table

Usage by features:
  from modules.quran.tashkeel_pref import get_pref, strip_tashkeel

  with_tashkeel = get_pref(uid, "khatma")      # True / False
  text = strip_tashkeel(text) if not with_tashkeel else text

Feature keys:
  "khatma"       → ختمتي
  "surah_read"   → قراءة سورة
  "ayah_search"  → آية [بحث]
"""
import re

from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.quran import quran_db as db

_B = "p"
_G = "su"
_R = "d"

# ── Feature metadata ──────────────────────────────────────────────
_FEATURES = {
    "khatma":      ("📖 ختمتي",       "khatma"),
    "surah_read":  ("📚 قراءة سورة",  "surah_read"),
    "ayah_search": ("🔍 آية",          "ayah_search"),
}

# ── Tashkeel regex (same as quran_service.remove_tashkeel) ────────
_TASHKEEL_RE = re.compile(
    r'['
    r'\u0610-\u061A'
    r'\u064B-\u065F'
    r'\u0670'
    r'\u0640'
    r'\u06D6-\u06DC'
    r'\u06DF-\u06E4'
    r'\u06E7-\u06E8'
    r'\u06EA-\u06ED'
    r']'
)


# ══════════════════════════════════════════
# Public helpers
# ══════════════════════════════════════════

def get_pref(user_id: int, feature: str) -> bool:
    """
    Returns True if the user wants tashkeel for this feature, False otherwise.
    Defaults to True (with tashkeel) if no preference is saved.
    """
    return db.get_quran_pref(user_id, feature)


def strip_tashkeel(text: str) -> str:
    """Removes all Arabic diacritics from text."""
    return _TASHKEEL_RE.sub("", text) if text else text


def apply_pref(text: str, with_tashkeel: bool) -> str:
    """Returns text with or without tashkeel based on preference."""
    return text if with_tashkeel else strip_tashkeel(text)


# ══════════════════════════════════════════
# Command handler
# ══════════════════════════════════════════

def handle_tashkeel_command(message) -> bool:
    """أمر: تشكيل الآيات — يفتح لوحة تفضيلات التشكيل."""
    if (message.text or "").strip() != "تشكيل الآيات":
        return False

    uid = message.from_user.id
    cid = message.chat.id
    _show_feature_picker(cid, uid, reply_to=message.message_id)
    return True


def _show_feature_picker(cid: int, uid: int, reply_to: int = None,
                          call=None) -> None:
    """Step 1: choose which feature to configure."""
    owner = (uid, cid)

    # Build current-state summary
    lines = []
    for key, (label, feat) in _FEATURES.items():
        pref  = db.get_quran_pref(uid, feat)
        badge = "📖 بالتشكيل" if pref else "📝 بدون تشكيل"
        lines.append(f"• {label}  →  {badge}")

    text = (
        f"⚙️ <b>تفضيلات التشكيل</b>\n{get_lines()}\n\n"
        + "\n".join(lines)
        + "\n\nاختر الميزة التي تريد تعديل إعدادها:"
    )

    buttons = [
        btn(label, "tsh_pick_feature", {"feat": feat}, owner=owner, color=_B)
        for _, (label, feat) in _FEATURES.items()
    ]
    buttons.append(btn("❌ إغلاق", "tsh_close", {}, owner=owner, color=_R))

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1, 1])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[1, 1, 1, 1],
                owner_id=uid, reply_to=reply_to)


@register_action("tsh_pick_feature")
def on_pick_feature(call, data):
    """Step 2: choose format for the selected feature."""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    feat = data.get("feat", "khatma")
    bot.answer_callback_query(call.id)

    # Find label for this feature
    label = next(
        (lbl for _, (lbl, f) in _FEATURES.items() if f == feat),
        feat
    )
    current = db.get_quran_pref(uid, feat)
    owner   = (uid, cid)

    text = (
        f"⚙️ <b>{label}</b>\n\n"
        f"الإعداد الحالي: {'📖 بالتشكيل' if current else '📝 بدون تشكيل'}\n\n"
        "اختر طريقة عرض الآيات:"
    )

    buttons = [
        btn(
            f"{'✅ ' if current else ''}📖 بالتشكيل",
            "tsh_set_pref",
            {"feat": feat, "val": 1},
            owner=owner,
            color=_G if current else _B,
        ),
        btn(
            f"{'✅ ' if not current else ''}📝 بدون تشكيل",
            "tsh_set_pref",
            {"feat": feat, "val": 0},
            owner=owner,
            color=_G if not current else _B,
        ),
        btn("🔙 رجوع", "tsh_back", {}, owner=owner, color=_R),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1])


@register_action("tsh_set_pref")
def on_set_pref(call, data):
    """Saves the preference and returns to the feature picker."""
    uid  = call.from_user.id
    cid  = call.message.chat.id
    feat = data.get("feat", "khatma")
    val  = bool(int(data.get("val", 1)))

    db.set_quran_pref(uid, feat, val)

    label = next(
        (lbl for _, (lbl, f) in _FEATURES.items() if f == feat),
        feat
    )
    badge = "📖 بالتشكيل" if val else "📝 بدون تشكيل"
    bot.answer_callback_query(call.id, f"✅ {label}: {badge}", show_alert=False)

    # Return to feature picker with updated state
    _show_feature_picker(cid, uid, call=call)


@register_action("tsh_back")
def on_back(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    _show_feature_picker(cid, uid, call=call)


@register_action("tsh_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

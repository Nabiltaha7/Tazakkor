"""
handlers/group_admin/developer/admin_panel.py
──────────────────────────────────────────────
لوحة إدارة المطور الرئيسية

أقسام:
  ⚙️  ثوابت البوت   — عرض وتعديل bot_constants
  👨‍💻 المطورون      — إضافة / إزالة / ترقية / تخفيض
  📿  إدارة الأذكار — إضافة / تعديل / حذف لكل فئة
  📖  إدارة القرآن  — بحث / تعديل / إضافة آيات / تفسير
  🔄  إعادة تحميل الآيات
"""
from core.bot import bot
from core.admin import (
    is_primary_dev, is_any_dev,
    get_all_constants, set_const,
    get_all_developers, add_developer, remove_developer,
    promote_developer, demote_developer,
)
from utils.pagination import (
    btn, send_ui, edit_ui, register_action, paginate_list, set_state, get_state, clear_state
)
from utils.helpers import get_lines
from database.db_queries.azkar_queries import (
    get_azkar_list, get_zikr, add_zikr, update_zikr, delete_zikr,
    # azkar_content (عام — type 4)
    get_azkar_content_by_id, count_azkar_content,
    insert_azkar_content, update_azkar_content, delete_azkar_content,
)
from database.connection import get_db_conn as _get_db_conn

_RED  = "d"
_GRN  = "su"
_BLUE = "p"

# أنواع الأذكار — type 4 يشير لجدول azkar_content (منفصل)
_ZIKR_TYPES = {
    0: "🌅 الصباح",
    1: "🌙 المساء",
    2: "😴 النوم",
    3: "☀️ الاستيقاظ",
    4: "🌐 عام",
}

# type 4 = azkar_content table (للنشر التلقائي في المجموعات)
_CONTENT_TYPE = 4


def _is_content_type(zikr_type: int) -> bool:
    return zikr_type == _CONTENT_TYPE


def _get_content_list(page: int, per_page: int) -> tuple[list, int]:
    """يجلب صفحة من azkar_content."""
    cur = _get_db_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM azkar_content")
    total = cur.fetchone()[0]
    cur.execute("SELECT id, content FROM azkar_content ORDER BY id LIMIT ? OFFSET ?",
                (per_page, page * per_page))
    items = [{"id": r[0], "text": r[1], "repeat_count": 1, "zikr_type": 4}
             for r in cur.fetchall()]
    return items, total

def _back(action, data, owner):
    return btn("🔙 رجوع", action, data, color=_RED, owner=owner)


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_admin_panel(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not is_any_dev(user_id):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return
    _send_main_panel(message)


def _send_main_panel(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    owner   = (user_id, chat_id)
    buttons = [
        btn("⚙️ ثوابت البوت",        "adm_constants",          {"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",           "adm_devs",               {},          owner=owner, color=_BLUE),
        btn("📿 إدارة الأذكار",       "adm_azkar_panel",        {},          owner=owner, color=_BLUE),
        btn("📖 إدارة القرآن",        "adm_quran_panel",        {},          owner=owner, color=_BLUE),
        btn("🔄 إعادة تحميل الآيات", "adm_reload_ayat_confirm",{},          owner=owner, color=_RED),
    ]
    send_ui(chat_id,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 1], owner_id=user_id, reply_to=message.message_id)


# ══════════════════════════════════════════
# 🛠 لوحة المطور (ثوابت البوت)
# ══════════════════════════════════════════

@register_action("adm_constants")
def show_constants(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        bot.answer_callback_query(call.id, " للمطورين فقط", show_alert=True)
        return

    page = int(data.get("page", 0))
    all_consts = get_all_constants()
    items, total_pages = paginate_list(all_consts, page, per_page=8)
    owner = (user_id, chat_id)

    # أرقام عربية للعرض
    _nums = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]

    text = f"🛠 لوحة المطور (صفحة {page+1}/{total_pages})\n‏• ━━━━━━━━━━━━ •\n\n"
    buttons = []
    for i, c in enumerate(items):
        num = _nums[i]
        text += f"{num} {c['name']} = <code>{c['value']}</code>\n{c['description']}\n\n"
        if is_primary_dev(user_id):
            buttons.append(btn(f"{i+1}", "adm_edit_const",
                               data={"name": c["name"], "page": page},
                               owner=owner, color=_BLUE))

    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي", "adm_constants", data={"page": page+1}, owner=owner))
    nav.append(_back("adm_main_back", {}, owner))
    if page > 0:
        nav.append(btn("السابق", "adm_constants", data={"page": page-1}, owner=owner))

    # أزرار الثوابت: 4 في كل صف
    btn_rows = [4] * (len(buttons) // 4)
    if len(buttons) % 4:
        btn_rows.append(len(buttons) % 4)
    layout = btn_rows + ([len(nav)] if nav else [1])

    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("adm_edit_const")
def edit_constant(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, " فقط المطور الأساسي يمكنه التعديل.", show_alert=True)
        return

    name = data["name"]
    page = data.get("page", 0)
    owner = (user_id, chat_id)

    set_state(user_id, chat_id, "adm_awaiting_const_value",
              data={"name": name, "page": page, "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل الثابت: {name}</b>\n\nأرسل القيمة الجديدة:",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 👨‍💻 إدارة المطورين
# ══════════════════════════════════════════

@register_action("adm_devs")
def show_developers(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, " فقط المطور الأساسي.", show_alert=True)
        return

    devs  = get_all_developers()
    owner = (user_id, chat_id)

    text = f"👨‍💻 <b>قائمة المطورين</b>\n{get_lines()}\n\n"
    buttons = []
    for d in devs:
        role_ar = "👑 أساسي" if d["role"] == "primary" else "🔧 ثانوي"
        text += f"{role_ar} — ID: <code>{d['user_id']}</code>\n"
        if d["user_id"] != user_id:
            if d["role"] == "secondary":
                buttons.append(btn(f"⬆️ ترقية {d['user_id']}", "adm_promote_dev",
                                   data={"uid": d["user_id"]}, owner=owner, color=_GRN))
            else:
                buttons.append(btn(f"⬇️ تخفيض {d['user_id']}", "adm_demote_dev",
                                   data={"uid": d["user_id"]}, owner=owner, color=_RED))
            buttons.append(btn(f"🗑 إزالة {d['user_id']}", "adm_remove_dev",
                               data={"uid": d["user_id"]}, owner=owner, color=_RED))

    buttons.append(btn("➕ إضافة مطور", "adm_add_dev_prompt", data={}, owner=owner, color=_GRN))
    buttons.append(_back("adm_main_back", {}, owner))

    layout = [2] * (len(buttons) // 2) + ([1] if len(buttons) % 2 else []) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("adm_promote_dev")
def promote_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, " للمطور الأساسي فقط.", show_alert=True)
        return
    promote_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تمت الترقية", show_alert=True)
    show_developers(call, {})


@register_action("adm_demote_dev")
def demote_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, " للمطور الأساسي فقط.", show_alert=True)
        return
    demote_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تم التخفيض", show_alert=True)
    show_developers(call, {})


@register_action("adm_remove_dev")
def remove_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, " للمطور الأساسي فقط.", show_alert=True)
        return
    ok = remove_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تمت الإزالة" if ok else " لا يمكن إزالة هذا المطور",
                              show_alert=True)
    show_developers(call, {})


@register_action("adm_add_dev_prompt")
def add_dev_prompt(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, " للمطور الأساسي فقط.", show_alert=True)
        return
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    set_state(user_id, chat_id, "adm_awaiting_new_dev",
              data={"_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "➕ <b>إضافة مطور جديد</b>\n\nأرسل ID المستخدم:",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 👑 رفع مطور / تنزيل مطور (أوامر نصية)
# ══════════════════════════════════════════

_NO_TARGET = (
    "❌ حدد المستخدم بإحدى الطرق:\n"
    "• الرد على رسالته\n"
    "• <code>@username</code>\n"
    "• رقم المعرف مثل: <code>123456789</code>"
)


def _resolve(message):
    from utils.user_resolver import resolve_user
    return resolve_user(message)


def _send_role_picker(cid: int, owner_uid: int, target_uid: int,
                      target_name: str, reply_to: int = None):
    """يرسل رسالة اختيار الدور مع زرين."""
    from utils.pagination.buttons import build_keyboard
    owner   = (owner_uid, cid)
    text    = (
        f"👤 <b>{target_name}</b> (<code>{target_uid}</code>)\n\n"
        f"اختر دور المطور:"
    )
    buttons = [
        btn("👑 مطور أساسي", "adm_set_dev_role",
            {"uid": target_uid, "name": target_name, "role": "primary"},
            owner=owner, color=_RED),
        btn("🔧 مطور ثانوي", "adm_set_dev_role",
            {"uid": target_uid, "name": target_name, "role": "secondary"},
            owner=owner, color=_BLUE),
        btn("❌ إلغاء",       "adm_dev_role_cancel", {},
            owner=owner, color=_RED),
    ]
    markup = build_keyboard(buttons, [2, 1], owner_uid)
    bot.send_message(cid, text, parse_mode="HTML",
                     reply_to_message_id=reply_to, reply_markup=markup)


def handle_promote_dev_command(message) -> bool:
    """أمر: رفع مطور — يقبل رد / @username / user_id"""
    text = (message.text or "").strip().lower()
    if text not in ("رفع مطور", "رفع_مطور"):
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if not is_primary_dev(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطور الأساسي فقط.")
        return True

    target_uid, target_name, err = _resolve(message)
    if not target_uid:
        bot.reply_to(message, err or _NO_TARGET, parse_mode="HTML")
        return True

    if target_uid == uid:
        bot.reply_to(message, "❌ لا يمكنك رفع نفسك.")
        return True

    _send_role_picker(cid, uid, target_uid, target_name,
                      reply_to=message.message_id)
    return True


def handle_demote_dev_command(message) -> bool:
    """أمر: تنزيل مطور — يزيل المستخدم من قائمة المطورين"""
    text = (message.text or "").strip().lower()
    if text not in ("تنزيل مطور", "تنزيل_مطور"):
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if not is_primary_dev(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطور الأساسي فقط.")
        return True

    target_uid, target_name, err = _resolve(message)
    if not target_uid:
        bot.reply_to(message, err or _NO_TARGET, parse_mode="HTML")
        return True

    if target_uid == uid:
        bot.reply_to(message, "❌ لا يمكنك تنزيل نفسك.")
        return True

    from database.db_queries.reports_queries import remove_developer_db, get_developer
    from core.config import developers_id as _DEFAULT_DEVS

    if target_uid in _DEFAULT_DEVS:
        bot.reply_to(message, "❌ لا يمكن إزالة المطور الأساسي الافتراضي.")
        return True

    dev = get_developer(target_uid)
    if not dev:
        bot.reply_to(
            message,
            f"⚠️ المستخدم <code>{target_uid}</code> ليس مطوراً.",
            parse_mode="HTML"
        )
        return True

    remove_developer_db(target_uid)
    role_ar = "👑 أساسي" if dev["role"] == "primary" else "🔧 ثانوي"
    bot.reply_to(
        message,
        f"✅ <b>تم تنزيل المطور</b>\n\n"
        f"👤 {target_name} (<code>{target_uid}</code>)\n"
        f"كان دوره: {role_ar}",
        parse_mode="HTML"
    )
    return True


@register_action("adm_set_dev_role")
def on_set_dev_role(call, data):
    """يحفظ الدور المختار في قاعدة البيانات."""
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return

    target_uid  = int(data["uid"])
    target_name = data.get("name", str(target_uid))
    role        = data.get("role", "secondary")

    from database.db_queries.reports_queries import upsert_developer, get_developer
    from database.db_queries.users_queries import ensure_user_exists

    # تأكد من وجود المستخدم في جدول users (FK constraint)
    ensure_user_exists(target_uid)
    upsert_developer(target_uid, role)

    role_ar = "👑 مطور أساسي" if role == "primary" else "🔧 مطور ثانوي"
    bot.answer_callback_query(call.id, f"✅ تم تعيين {role_ar}", show_alert=True)

    try:
        bot.edit_message_text(
            f"✅ <b>تم رفع المطور</b>\n\n"
            f"👤 {target_name} (<code>{target_uid}</code>)\n"
            f"الدور: {role_ar}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


@register_action("adm_dev_role_cancel")
def on_dev_role_cancel(call, data):
    bot.answer_callback_query(call.id, "تم الإلغاء.")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔙 رجوع للرئيسية
# ══════════════════════════════════════════

@register_action("adm_main_back")
def back_to_main(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if not is_any_dev(user_id):
        return
    owner = (user_id, chat_id)
    buttons = [
        btn("⚙️ ثوابت البوت",        "adm_constants",          {"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",           "adm_devs",               {},          owner=owner, color=_BLUE),
        btn("📿 إدارة الأذكار",       "adm_azkar_panel",        {},          owner=owner, color=_BLUE),
        btn("📖 إدارة القرآن",        "adm_quran_panel",        {},          owner=owner, color=_BLUE),
        btn("🔄 إعادة تحميل الآيات", "adm_reload_ayat_confirm",{},          owner=owner, color=_RED),
    ]
    edit_ui(call,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 1])


# ══════════════════════════════════════════
# 📝 معالج الإدخال النصي
# ══════════════════════════════════════════

def handle_admin_input(message) -> bool:
    """
    يعالج الإدخال النصي لحالات الانتظار في لوحة الإدارة.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_any_dev(user_id):
        return False

    state = get_state(user_id, chat_id)
    if not state or "state" not in state:
        return False

    s = state["state"]

    # ── يتعامل فقط مع حالات admin_panel ──
    _HANDLED_STATES = {
        "adm_awaiting_const_value",
        "adm_awaiting_new_dev",
        "adm_awaiting_add_zikr",
        "adm_awaiting_edit_zikr",
    }
    if s not in _HANDLED_STATES:
        return False

    sdata = state.get("data", {})
    text  = (message.text or "").strip()
    mid   = sdata.get("_mid")   # get بدلاً من pop
    clear_state(user_id, chat_id)

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    def _edit(msg_text):
        if mid:
            try:
                bot.edit_message_text(msg_text, chat_id, mid, parse_mode="HTML")
            except Exception:
                pass

    # ─── تعديل ثابت ───
    if s == "adm_awaiting_const_value":
        name = sdata.get("name")
        if set_const(name, text):
            _edit(f"✅ تم تحديث <b>{name}</b> = <code>{text}</code>")
        else:
            _edit(f"❌ فشل تحديث الثابت <b>{name}</b>")
        return True

    # ─── إضافة مطور ───
    if s == "adm_awaiting_new_dev":
        if not is_primary_dev(user_id):
            return True
        parts   = text.split()
        uid_str = parts[0] if parts else ""
        role    = parts[1] if len(parts) > 1 and parts[1] in ("primary", "secondary") else "secondary"
        if uid_str.isdigit():
            add_developer(int(uid_str), role)
            _edit(f"✅ تمت إضافة المطور <code>{uid_str}</code> كـ {role}")
        else:
            _edit("❌ ID غير صالح. أرسل رقماً مثل: <code>123456789</code>")
        return True

    # ─── إضافة ذكر جديد ───
    if s == "adm_awaiting_add_zikr":
        zikr_type  = sdata.get("zikr_type", 0)
        zikr_text  = text.strip()
        if not zikr_text:
            _edit("❌ النص لا يمكن أن يكون فارغاً.")
            return True

        if _is_content_type(zikr_type):
            new_id = insert_azkar_content(zikr_text)
            type_label = _ZIKR_TYPES.get(zikr_type, str(zikr_type))
            _edit(f"✅ تمت إضافة الذكر #{new_id} إلى {type_label}")
        else:
            if "|" in text:
                parts = text.split("|", 1)
                zikr_text = parts[0].strip()
                try:
                    repeat = int(parts[1].strip())
                except ValueError:
                    repeat = 1
            else:
                repeat = 1
            if zikr_text:
                new_id = add_zikr(zikr_text, repeat, zikr_type)
                type_label = _ZIKR_TYPES.get(zikr_type, str(zikr_type))
                _edit(f"✅ تمت إضافة الذكر #{new_id} إلى {type_label}\nالتكرار: {repeat}x")
            else:
                _edit("❌ النص لا يمكن أن يكون فارغاً.")
        return True

    # ─── تعديل ذكر ───
    if s == "adm_awaiting_edit_zikr":
        zikr_id   = sdata.get("zikr_id")
        zikr_type = sdata.get("zikr_type", 0)

        if _is_content_type(zikr_type):
            new_text = text.strip()
            if new_text:
                update_azkar_content(zikr_id, new_text)
                _edit(f"✅ تم تعديل الذكر #{zikr_id}")
            else:
                _edit("❌ النص لا يمكن أن يكون فارغاً.")
        else:
            zikr = get_zikr(zikr_id)
            if not zikr:
                _edit("❌ الذكر غير موجود.")
                return True
            if "|" in text:
                parts    = text.split("|", 1)
                new_text = parts[0].strip()
                try:
                    repeat = int(parts[1].strip())
                except ValueError:
                    repeat = zikr["repeat_count"]
            else:
                new_text = text.strip()
                repeat   = zikr["repeat_count"]
            if new_text:
                update_zikr(zikr_id, new_text, repeat)
                _edit(f"✅ تم تعديل الذكر #{zikr_id}")
            else:
                _edit("❌ النص لا يمكن أن يكون فارغاً.")
        return True

    return False


# ══════════════════════════════════════════
# 📿 إدارة الأذكار — القائمة الرئيسية
# ══════════════════════════════════════════

@register_action("adm_azkar_panel")
def adm_azkar_panel(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    text = f"📿 <b>إدارة الأذكار</b>\n{get_lines()}\nاختر الفئة:"
    buttons = [
        btn(label, "adm_azkar_list", {"type": t, "page": 0}, owner=owner, color=_BLUE)
        for t, label in _ZIKR_TYPES.items()
    ]
    buttons.append(_back("adm_main_back", {}, owner))
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 1, 1])


# ══════════════════════════════════════════
# 📋 قائمة الأذكار لفئة معينة
# ══════════════════════════════════════════

@register_action("adm_azkar_list")
def adm_azkar_list(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid       = call.from_user.id
    cid       = call.message.chat.id
    owner     = (uid, cid)
    zikr_type = int(data.get("type", 0))
    page      = int(data.get("page", 0))
    per_page  = 5
    type_label = _ZIKR_TYPES.get(zikr_type, str(zikr_type))

    # ── جلب البيانات حسب الجدول ──
    if _is_content_type(zikr_type):
        items, total = _get_content_list(page, per_page)
    else:
        all_azkar = get_azkar_list(zikr_type)
        total     = len(all_azkar)
        start     = page * per_page
        items     = all_azkar[start: start + per_page]

    total_pages = max(1, (total + per_page - 1) // per_page)

    text = (
        f"📿 <b>{type_label}</b>\n{get_lines()}\n"
        f"الإجمالي: {total} ذكر — صفحة {page+1}/{total_pages}\n\n"
    )
    buttons = []
    for z in items:
        preview = z["text"][:40].replace("\n", " ")
        text += f"<b>#{z['id']}</b> {preview}…\n"
        buttons.append(btn(
            f"#{z['id']} — {preview[:25]}",
            "adm_azkar_view", {"zid": z["id"], "type": zikr_type, "page": page},
            owner=owner, color=_BLUE
        ))

    nav = []
    if page > 0:
        nav.append(btn("▶️ السابق", "adm_azkar_list", {"type": zikr_type, "page": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "adm_azkar_list", {"type": zikr_type, "page": page + 1}, owner=owner))

    buttons += nav
    buttons.append(btn("➕ إضافة ذكر", "adm_azkar_add", {"type": zikr_type, "page": page}, owner=owner, color=_GRN))
    buttons.append(_back("adm_azkar_panel", {}, owner))

    layout = [1] * len(items) + ([len(nav)] if nav else []) + [1, 1]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# 🔍 عرض ذكر واحد
# ══════════════════════════════════════════

@register_action("adm_azkar_view")
def adm_azkar_view(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid       = call.from_user.id
    cid       = call.message.chat.id
    owner     = (uid, cid)
    zikr_id   = int(data["zid"])
    zikr_type = int(data.get("type", 0))
    page      = int(data.get("page", 0))

    if _is_content_type(zikr_type):
        row = get_azkar_content_by_id(zikr_id)
        if not row:
            bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
            return
        zikr = {"id": row["id"], "text": row["content"], "repeat_count": 1, "zikr_type": 4}
    else:
        zikr = get_zikr(zikr_id)
        if not zikr:
            bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
            return

    type_label = _ZIKR_TYPES.get(zikr_type, str(zikr_type))
    repeat_line = "" if _is_content_type(zikr_type) else f"🔢 التكرار: <b>{zikr['repeat_count']}x</b>\n\n"
    text = (
        f"📿 <b>ذكر #{zikr_id}</b>\n{get_lines()}\n\n"
        f"📂 الفئة: {type_label}\n"
        f"{repeat_line}"
        f"📝 النص:\n{zikr['text']}"
    )
    buttons = [
        btn("✏️ تعديل", "adm_azkar_edit",
            {"zid": zikr_id, "type": zikr_type, "page": page}, owner=owner, color=_BLUE),
    ]
    if is_primary_dev(uid):
        buttons.append(btn("🗑 حذف", "adm_azkar_delete_confirm",
                           {"zid": zikr_id, "type": zikr_type, "page": page},
                           owner=owner, color=_RED))
    buttons.append(_back("adm_azkar_list", {"type": zikr_type, "page": page}, owner))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1] if len(buttons) == 3 else [1, 1])


# ══════════════════════════════════════════
# ✏️ تعديل ذكر
# ══════════════════════════════════════════

@register_action("adm_azkar_edit")
def adm_azkar_edit(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_id   = int(data["zid"])
    zikr_type = int(data.get("type", 0))

    if _is_content_type(zikr_type):
        row = get_azkar_content_by_id(zikr_id)
        if not row:
            bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
            return
        current_text = row["content"]
        hint = "أرسل النص الجديد:"
    else:
        zikr = get_zikr(zikr_id)
        if not zikr:
            bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
            return
        current_text = zikr["text"]
        hint = "أرسل النص الجديد بالصيغة:\n<code>النص | عدد_التكرار</code>\nأو النص فقط للإبقاء على نفس عدد التكرار."

    set_state(uid, cid, "adm_awaiting_edit_zikr", data={
        "zikr_id":   zikr_id,
        "zikr_type": zikr_type,
        "page":      int(data.get("page", 0)),
        "_mid":      call.message.message_id,
    })
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل ذكر #{zikr_id}</b>\n{get_lines()}\n\n"
            f"النص الحالي:\n<code>{current_text[:200]}</code>\n\n"
            f"{hint}",
            cid, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🗑 حذف ذكر
# ══════════════════════════════════════════

@register_action("adm_azkar_delete_confirm")
def adm_azkar_delete_confirm(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid     = call.from_user.id
    cid     = call.message.chat.id
    owner   = (uid, cid)
    zikr_id = int(data["zid"])
    zikr    = get_zikr(zikr_id)
    if not zikr:
        bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
        return

    preview = zikr["text"][:60].replace("\n", " ")
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"⚠️ <b>تأكيد الحذف</b>\n{get_lines()}\n\n"
                 f"هل تريد حذف الذكر #{zikr_id}؟\n\n<i>{preview}</i>",
            buttons=[
                btn("🗑 تأكيد الحذف", "adm_azkar_delete_execute",
                    {"zid": zikr_id, "type": data.get("type", 0), "page": data.get("page", 0)},
                    owner=owner, color=_RED),
                _back("adm_azkar_view",
                      {"zid": zikr_id, "type": data.get("type", 0), "page": data.get("page", 0)},
                      owner),
            ],
            layout=[1, 1])


@register_action("adm_azkar_delete_execute")
def adm_azkar_delete_execute(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    zikr_id   = int(data["zid"])
    zikr_type = int(data.get("type", 0))
    page      = int(data.get("page", 0))

    if _is_content_type(zikr_type):
        ok = delete_azkar_content(zikr_id)
    else:
        ok = delete_zikr(zikr_id)

    bot.answer_callback_query(call.id, "✅ تم الحذف" if ok else "❌ فشل الحذف", show_alert=True)
    adm_azkar_list(call, {"type": zikr_type, "page": page})


# ══════════════════════════════════════════
# ➕ إضافة ذكر جديد
# ══════════════════════════════════════════

@register_action("adm_azkar_add")
def adm_azkar_add(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid        = call.from_user.id
    cid        = call.message.chat.id
    zikr_type  = int(data.get("type", 0))
    page       = int(data.get("page", 0))
    type_label = _ZIKR_TYPES.get(zikr_type, str(zikr_type))

    set_state(uid, cid, "adm_awaiting_add_zikr", data={
        "zikr_type": zikr_type,
        "page":      page,
        "_mid":      call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    if _is_content_type(zikr_type):
        hint = (
            f"➕ <b>إضافة ذكر — {type_label}</b>\n{get_lines()}\n\n"
            f"أرسل نص الذكر:\n\n"
            f"<i>يُستخدم للنشر التلقائي في المجموعات</i>"
        )
    else:
        hint = (
            f"➕ <b>إضافة ذكر — {type_label}</b>\n{get_lines()}\n\n"
            f"أرسل الذكر بالصيغة:\n"
            f"<code>النص | عدد_التكرار</code>\n\n"
            f"مثال:\n<code>سبحان الله | 33</code>\n\n"
            f"أو أرسل النص فقط (التكرار الافتراضي = 1)."
        )
    try:
        bot.edit_message_text(hint, cid, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


@register_action("adm_quran_panel")
def adm_quran_panel(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    from handlers.group_admin.developer.dev_control_panel import _show_quran_dev_panel
    _show_quran_dev_panel(call)


# ══════════════════════════════════════════
# 🔄 إعادة تحميل الآيات
# ══════════════════════════════════════════

@register_action("adm_reload_ayat_confirm")
def reload_ayat_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, " فقط المطور الأساسي.", show_alert=True)
        return

    owner = (user_id, chat_id)
    edit_ui(
        call,
        text=(
            "⚠️ <b>إعادة تحميل الآيات</b>\n"
            f"{get_lines()}\n\n"
            "سيتم <b>حذف جميع الآيات</b> من قاعدة البيانات\n"
            "وإعادة تحميلها من API.\n\n"
            "⚠️ <b>هذا الإجراء لا يمكن التراجع عنه!</b>\n\n"
            "هل أنت متأكد؟"
        ),
        buttons=[
            btn("✅ تأكيد الإعادة", "adm_reload_ayat_execute", data={},
                owner=owner, color=_RED),
            btn(" إلغاء", "adm_main_back", data={},
                owner=owner, color=_GRN),
        ],
        layout=[1, 1],
    )


@register_action("adm_reload_ayat_execute")
def reload_ayat_execute(call, data):
    import threading

    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, " للمطور الأساسي فقط.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري إعادة التحميل...")

    # ── إنشاء رسالة التقدم الوحيدة ──
    header   = "🔄 <b>إعادة تحميل الآيات</b>\n" + get_lines() + "\n\n"
    init_msg = header + "⏳ جاري التحميل...\nقد تستغرق العملية بعض الوقت."

    try:
        progress_msg = bot.send_message(chat_id, init_msg, parse_mode="HTML")
        prog_mid     = progress_msg.message_id
    except Exception:
        prog_mid = None

    # ── تراكم سطور التقدم وتحديث الرسالة ──
    lines = []

    def _edit_progress():
        if not prog_mid:
            return
        body = "\n".join(lines[-60:])   # آخر 60 سطر لتجنب تجاوز حد تيليغرام
        try:
            bot.edit_message_text(
                header + body,
                chat_id, prog_mid, parse_mode="HTML"
            )
        except Exception:
            pass

    def _progress(msg: str):
        lines.append(msg)
        _edit_progress()

    # ── تشغيل العملية في thread منفصل لعدم تجميد البوت ──
    def _run():
        from modules.quran import quran_db as qr_db
        ok, summary = qr_db.reload_ayat_from_api(progress_callback=_progress)

        final = header + "\n".join(lines[-60:]) + f"\n\n{'✅' if ok else ''} {summary}"
        if prog_mid:
            try:
                bot.edit_message_text(final, chat_id, prog_mid, parse_mode="HTML")
                return
            except Exception:
                pass
        bot.send_message(chat_id, f"{'✅' if ok else ''} {summary}", parse_mode="HTML")

    threading.Thread(target=_run, daemon=True).start()

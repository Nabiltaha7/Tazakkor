"""
محرك التدفق — يستبدل سلاسل if/elif المتداخلة في handle_developer_input.

كل تدفق هو قاموس:  step_name → handler_function(message, state, ctx)

ctx هو dict يحتوي على:
  uid, cid, raw, mid, owner, sdata
"""
from core.bot import bot
from core.state_manager import StateManager
from utils.pagination import btn, paginate_list
from utils.pagination.buttons import build_keyboard
from utils.ui_helpers import send_or_edit, prompt_with_cancel, cancel_buttons

from modules.quran import quran_db as qr_db
from modules.quran import quran_service as qr_svc
from utils.helpers import get_lines

_B = "p"
_G = "su"
_R = "d"
_PER_PAGE = 5


# ══════════════════════════════════════════
# مساعد مشترك
# ══════════════════════════════════════════

def _show_result(ctx: dict, text: str, buttons: list = None, layout: list = None):
    """يعرض نتيجة مع أزرار رجوع/إغلاق افتراضية."""
    uid, cid, mid = ctx["uid"], ctx["cid"], ctx["mid"]
    if buttons is None:
        buttons, layout = cancel_buttons((uid, cid))
    send_or_edit(cid, text, message_id=mid, buttons=buttons,
                layout=layout, owner_id=uid)


def _prompt(ctx: dict, text: str, cancel_action: str = "qr_dev_cancel") -> int | None:
    """يعرض رسالة طلب إدخال مع زر إلغاء."""
    uid, cid, mid = ctx["uid"], ctx["cid"], ctx["mid"]
    new_mid = prompt_with_cancel(cid, uid, text, message_id=mid,
                                 cancel_action=cancel_action)
    if new_mid and new_mid != mid:
        StateManager.set_mid(uid, cid, new_mid)
    return new_mid


# ══════════════════════════════════════════
# FLOW: Quran — Search
# ══════════════════════════════════════════

def _qr_search(message, state: dict, ctx: dict):
    raw     = ctx["raw"]
    uid, cid, mid = ctx["uid"], ctx["cid"], ctx["mid"]
    results = qr_svc.search(raw)
    if not results:
        _show_result(ctx, f"🔍 لم يتم العثور على نتائج لـ: <b>{raw}</b>")
        return True
    _show_qr_search_results(uid, cid, raw, results, page=0, mid=mid)
    return True


def _show_qr_search_results(uid, cid, query, results, page, mid):
    items, total_pages = paginate_list(results, page, per_page=_PER_PAGE)
    text = f"🔍 <b>نتائج البحث: {query}</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    for r in items:
        text += f"📖 <b>{r['sura_name']}</b> — آية {r['ayah_number']}\n{r['text_with_tashkeel']}\n\n"

    owner   = (uid, cid)
    buttons = [
        btn(f"📖 {r['sura_name']} {r['ayah_number']}", "qr_dev_select_ayah",
            {"aid": r["id"]}, color=_B, owner=owner)
        for r in items
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "qr_dev_search_page", {"q": query, "p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "qr_dev_search_page", {"q": query, "p": page + 1}, owner=owner))
    nav.append(btn("❌ إغلاق", "qr_dev_cancel", {}, color=_R, owner=owner))
    buttons += nav
    layout   = [1] * len(items) + ([len(nav)] if nav else [1])
    send_or_edit(cid, text, message_id=mid, buttons=buttons, layout=layout, owner_id=uid)


# ══════════════════════════════════════════
# FLOW: Quran — Edit Ayah (find step)
# ══════════════════════════════════════════

def _qr_edit_ayah_find(message, state: dict, ctx: dict):
    raw = ctx["raw"]
    parts = raw.split()
    if not parts:
        _show_result(ctx, "❌ أدخل اسم السورة ورقم الآية.")
        return True

    if len(parts) == 1 and parts[0].isdigit():
        ayah = qr_db.get_ayah(int(parts[0]))
    else:
        ayah_num  = parts[-1] if parts[-1].isdigit() else None
        sura_name = " ".join(parts[:-1] if ayah_num else parts)
        if not ayah_num:
            _show_result(ctx, "❌ أدخل رقم الآية.")
            return True
        ayah = qr_db.get_ayah_by_sura_number(sura_name, int(ayah_num))

    if not ayah:
        _show_result(ctx, "❌ الآية غير موجودة.")
        return True

    uid, cid, mid = ctx["uid"], ctx["cid"], ctx["mid"]
    owner = (uid, cid)
    text  = (
        f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"{get_lines()}\n\n{ayah['text_with_tashkeel']}\n\n"
        f"{get_lines()}\n<i>آية #{ayah['id']}</i>"
    )
    buttons = [
        btn("✏️ تعديل النص", "qr_dev_edit_ayah_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("⬅️ رجوع",       "qr_dev_edit_ayah",          {},                  color=_R, owner=owner),
    ]
    send_or_edit(cid, text, message_id=mid, buttons=buttons, layout=[2], owner_id=uid)
    return True


# ══════════════════════════════════════════
# FLOW: Quran — Edit Tafseer (find step)
# ══════════════════════════════════════════

def _qr_edit_tafseer_find(message, state: dict, ctx: dict):
    raw = ctx["raw"]
    if not raw.isdigit():
        _show_result(ctx, "❌ أرسل رقماً صحيحاً.")
        return True
    ayah = qr_db.get_ayah(int(raw))
    if not ayah:
        _show_result(ctx, f"❌ لا توجد آية بالرقم {raw}.")
        return True

    uid, cid, mid = ctx["uid"], ctx["cid"], ctx["mid"]
    owner   = (uid, cid)
    text    = (
        f"📖 <b>تعديل تفسير</b>\n"
        f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"{get_lines()}\n\nاختر نوع التفسير:"
    )
    buttons = [
        btn(name_ar, "qr_dev_choose_tafseer",
            {"aid": ayah["id"], "col": col}, color=_B, owner=owner)
        for name_ar, col in qr_db.TAFSEER_TYPES.items()
    ]
    buttons.append(btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner))
    send_or_edit(cid, text, message_id=mid, buttons=buttons, layout=[3,1], owner_id=uid)
    return True


# ══════════════════════════════════════════
# FLOW: Quran — Add Ayat (3 steps)
# ══════════════════════════════════════════

def _qr_add_sura(message, state: dict, ctx: dict):
    """الخطوة 1: استقبال اسم السورة."""
    raw = ctx["raw"]
    if not raw:
        _show_result(ctx, "❌ أدخل اسم السورة.")
        return True

    uid, cid = ctx["uid"], ctx["cid"]
    StateManager.set(uid, cid, {
        "type":  "qr_dev_add",
        "step":  "await_start",
        "mid":   ctx["mid"],
        "extra": {"sura": raw},
    }, ttl=300)

    new_mid = _prompt(
        ctx,
        f"➕ <b>إضافة آيات — سورة {raw}</b>\n\n"
        f"أرسل رقم الآية الأولى (أو أرسل أي شيء للبدء من 1):",
        cancel_action="qr_dev_cancel",
    )
    if new_mid:
        StateManager.set_mid(uid, cid, new_mid)
    return True


def _qr_add_start(message, state: dict, ctx: dict):
    """الخطوة 2: استقبال رقم البداية."""
    raw       = ctx["raw"]
    extra     = state.get("extra") or {}
    sura_name = extra.get("sura", "")
    start_num = int(raw) if raw.isdigit() else 1

    uid, cid = ctx["uid"], ctx["cid"]
    StateManager.set(uid, cid, {
        "type":  "qr_dev_add",
        "step":  "await_text",
        "mid":   ctx["mid"],
        "extra": {"sura": sura_name, "start": start_num},
    }, ttl=300)

    new_mid = _prompt(
        ctx,
        f"➕ <b>إضافة آيات — سورة {sura_name}</b>\n"
        f"بداية من الآية رقم: <b>{start_num}</b>\n\n"
        f"أرسل الآيات. لإضافة عدة آيات دفعة واحدة، افصل بينها بـ:\n"
        f"<code>{qr_db.BULK_SEPARATOR}</code>",
        cancel_action="qr_dev_cancel",
    )
    if new_mid:
        StateManager.set_mid(uid, cid, new_mid)
    return True


def _qr_add_text(message, state: dict, ctx: dict):
    """الخطوة 3: استقبال نص الآيات وإدراجها."""
    raw   = ctx["raw"]
    extra = state.get("extra") or {}
    sura_name = extra.get("sura", "")
    start_num = extra.get("start", 1)

    if not raw:
        _show_result(ctx, "❌ النص لا يمكن أن يكون فارغاً.")
        return True

    added = qr_svc.bulk_add_ayat(sura_name, start_num, raw)
    _show_result(
        ctx,
        f"✅ تمت إضافة <b>{added}</b> آية إلى سورة <b>{sura_name}</b>.\n"
        f"الفاصل المستخدم: <code>{qr_db.BULK_SEPARATOR}</code>",
    )
    return True


# ══════════════════════════════════════════
# FLOW: Quran — Edit Ayah Text
# ══════════════════════════════════════════

def _qr_edit_ayah_text(message, state: dict, ctx: dict):
    raw   = ctx["raw"]
    extra = state.get("extra") or ctx["sdata"]
    aid   = extra.get("aid")
    if not raw:
        _show_result(ctx, "❌ النص لا يمكن أن يكون فارغاً.")
        return True
    ok = qr_svc.edit_ayah(aid, raw)
    _show_result(ctx, "✅ تم تعديل نص الآية." if ok else "❌ فشل التعديل.")
    return True


# ══════════════════════════════════════════
# FLOW: Quran — Edit Tafseer Text
# ══════════════════════════════════════════

def _qr_edit_tafseer_text(message, state: dict, ctx: dict):
    from utils.logger import log_event
    log_event("tafseer_input_received", text=message.text)

    # هذه الميزة تعمل فقط داخل المجموعات
    if message.chat.type == "private":
        send_or_edit(
            chat_id=ctx["cid"],
            text="❌ هذه الميزة تعمل فقط داخل القروبات",
        )
        return True

    raw   = ctx["raw"]
    extra = state.get("extra") or ctx["sdata"]
    aid   = extra.get("aid")
    col   = extra.get("col")
    if not raw:
        _show_result(ctx, "❌ النص لا يمكن أن يكون فارغاً.")
        return True
    ok = qr_svc.edit_tafseer(aid, col, raw)
    _show_result(ctx, "✅ تم تعديل التفسير." if ok else "❌ فشل التعديل.")
    return True


# ══════════════════════════════════════════
# تعريف التدفقات
# ══════════════════════════════════════════


# Quran — حالات مستقلة + تدفق متعدد الخطوات
FLOW_QURAN_DEV: dict[str, callable] = {
    "qr_dev_awaiting_search":       _qr_search,
    "qr_dev_awaiting_edit_ayah":    _qr_edit_ayah_find,
    "qr_dev_awaiting_edit_tafseer": _qr_edit_tafseer_find,
    # تدفق الإضافة — الخطوات مُوحَّدة تحت نوع واحد "qr_dev_add"
    "qr_dev_awaiting_sura":         _qr_add_sura,    # legacy key
    "qr_dev_edit_ayah_text":        _qr_edit_ayah_text,
    # تفسير — step-based: type="qr_dev_edit_tafseer", step="await_text"
    "qr_dev_edit_tafseer":          _qr_edit_tafseer_text,
    # legacy key — kept for backward compat
    "qr_dev_edit_tafseer_text":     _qr_edit_tafseer_text,
}

# تدفق التفسير متعدد الخطوات — مُفهرَس بالخطوة
FLOW_QR_TAFSEER_STEPS: dict[str, callable] = {
    "await_text": _qr_edit_tafseer_text,
}

# تدفق الإضافة متعدد الخطوات — مُفهرَس بالخطوة
FLOW_QR_ADD_STEPS: dict[str, callable] = {
    "await_sura":  _qr_add_sura,
    "await_start": _qr_add_start,
    "await_text":  _qr_add_text,
}


def dispatch(message, uid: int, cid: int) -> bool:
    """
    نقطة الدخول الموحدة للمحرك.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    from core.state_manager import StateManager
    from core.admin import is_any_dev
    from utils.logger import log_event

    if not is_any_dev(uid):
        return False

    state = StateManager.get(uid, cid)
    if not state:
        return False

    state_type = state.get("type", "")
    step       = state.get("step")

    # لا نتعامل إلا مع حالات qr_dev_
    if not (state_type.startswith("qr_dev_") or
            state_type == "qr_dev_add"):
        return False

    raw   = (message.text or "").strip()
    mid   = state.get("mid")
    sdata = state.get("extra") or {}

    ctx = {
        "uid":   uid,
        "cid":   cid,
        "raw":   raw,
        "mid":   mid,
        "owner": (uid, cid),
        "sdata": sdata,
    }

    # ── تحديد الـ handler أولاً قبل أي مسح ──
    handler = None

    if state_type == "qr_dev_edit_tafseer":
        log_event("tafseer_input", text=message.text)
        handler = FLOW_QR_TAFSEER_STEPS.get(step) if step else _qr_edit_tafseer_text

    elif state_type == "qr_dev_add":
        handler = FLOW_QR_ADD_STEPS.get(step)

    else:
        handler = FLOW_QURAN_DEV.get(state_type)

    # إذا لم يوجد handler → لا نمسح الحالة، نتركها لـ handle_dev_quran_input
    if not handler:
        log_event("flow_no_handler", type=state_type, step=step)
        return False

    # ── الآن فقط: مسح الحالة + حذف رسالة المستخدم ──
    StateManager.clear(uid, cid)
    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    log_event("flow_step", type=state_type, step=step)
    try:
        return handler(message, state, ctx)
    except Exception as e:
        log_event("flow_error", error=str(e))
        StateManager.clear(uid, cid)
        send_or_edit(
            chat_id=cid,
            text="❌ حدث خطأ أثناء التنفيذ، تم إلغاء العملية",
        )
        return True


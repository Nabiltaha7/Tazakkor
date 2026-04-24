"""
ختمة القرآن — تتبع التقدم الكلي مع streak، إنجازات، وتذكيرات يومية.
"""
import random
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.quran import quran_db as db
from database.db_queries.timezone_queries import get_user_tz, set_user_tz

_B = "p"
_G = "su"
_R = "d"
_GOAL_VALUES   = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
_MAX_REMINDERS = 2

_MOTIVATIONAL = [
    "✨ استمر! أنت قريب من إنهاء الختمة",
    "🔥 أداء رائع! حافظ على السلسلة",
    "💪 تقدم ممتاز، لا تتوقف الآن",
    "📖 كل آية تقرأها نور في قلبك",
    "🌟 أنت على الطريق الصحيح، واصل",
    "🕌 القرآن رفيق الدنيا والآخرة",
]


def _fmt12(h: int, m: int) -> str:
    period = "AM" if h < 12 else "PM"
    h12    = h % 12 or 12
    return f"{h12:02d}:{m:02d} {period}"


def _fmt_hour(h: int) -> str:
    """يعرض الساعة بتنسيق 12 ساعة مع ص/م."""
    period = "ص" if h < 12 else "م"
    h12    = h % 12 or 12
    return f"{h12:02d} {period}"


def _inactive_msg(days: int) -> str:
    if days <= 0:
        return ""
    if days <= 2:
        return f"😴 غبت {days} يوم، ارجع لختمتك"
    if days <= 5:
        return f"👀 {days} أيام غياب، لا تخسر تقدمك"
    return f"💔 {days} أيام بدون قراءة — نفتقدك!"


# ══════════════════════════════════════════
# Entry points
# ══════════════════════════════════════════

def handle_khatmah_read_command(message) -> bool:
    """
    أمر: ختمتي — يعرض الآية التالية مباشرة بدون قوائم.
    رسالة قراءة نظيفة بدون أزرار.
    """
    if (message.text or "").strip() != "ختمتي":
        return False
    uid = message.from_user.id
    cid = message.chat.id

    k    = db.get_khatma(uid)
    ayah = db.get_ayah_by_sura_number(k["last_surah"], k["last_ayah"])
    if not ayah:
        ayah = db.get_first_ayah()
    if not ayah:
        bot.reply_to(message, "📖 لا توجد آيات في قاعدة البيانات بعد.")
        return True

    # Read preference once at session start — no per-ayah DB queries
    from modules.quran.tashkeel_pref import get_pref
    with_tashkeel = get_pref(uid, "khatma")

    from modules.quran.surah_reader import _show_khatmah_ayah
    _show_khatmah_ayah(uid, cid, ayah, reply_to=message.message_id,
                       with_tashkeel=with_tashkeel)
    _announce_achievements(uid, cid)
    return True


def handle_khatmah_settings_command(message) -> bool:
    """أمر: إعدادات ختمة — يفتح لوحة الإعدادات والإحصائيات."""
    if (message.text or "").strip() != "إعدادات ختمة":
        return False
    uid = message.from_user.id
    cid = message.chat.id
    _show_khatmah_settings(cid, uid, reply_to=message.message_id)
    return True


def handle_khatmah_reminder_command(message) -> bool:
    if (message.text or "").strip() != "تذكير ختمتي":
        return False
    uid = message.from_user.id
    cid = message.chat.id
    _show_reminder_panel(cid, uid, reply_to=message.message_id)
    return True


# ══════════════════════════════════════════
# Settings panel
# ══════════════════════════════════════════

def _show_khatmah_settings(cid, uid, reply_to=None, call=None):
    k        = db.get_khatma(uid)
    total    = k["total_read"]
    pct      = min(100.0, (total / db.TOTAL_QURAN_AYAT) * 100)
    goal     = db.get_khatma_goal(uid)
    today    = db.get_today_count(uid)
    streak   = db.get_streak(uid)
    best_day = db.get_best_day(uid)
    days_off = db.get_days_since_last_read(uid)

    sura      = db.get_sura(k["last_surah"])
    sura_name = sura["name"] if sura else f"سورة {k['last_surah']}"

    filled   = int(pct / 100 * 12)
    bar      = "█" * filled + "░" * (12 - filled)
    daily_pct  = min(100, int(today / goal * 100)) if goal > 0 else 0
    daily_fill = int(daily_pct / 100 * 10)
    daily_bar  = "▓" * daily_fill + "░" * (10 - daily_fill)

    goal_badge = "\n🎉 <b>أحسنت! أكملت هدفك اليومي</b>" if today >= goal > 0 else ""

    if streak >= 7:
        streak_line = f"\n🔥 <b>سلسلة قوية! {streak} يوم — لا تخسرها</b>"
    elif streak >= 2:
        streak_line = f"\n🔥 <b>{streak} أيام متواصلة</b>"
    elif streak == 1:
        streak_line = "\n🔥 يوم واحد — ابدأ سلسلتك!"
    else:
        streak_line = ""

    if total == 0:
        motivational = "📖 ابدأ رحلتك مع القرآن الكريم"
    elif days_off >= 1:
        motivational = _inactive_msg(days_off)
    elif streak >= 7:
        motivational = "🔥 سلسلة قوية! لا تخسرها"
    else:
        motivational = random.choice(_MOTIVATIONAL)

    best_line = f"\n🏅 أفضل يوم: <b>{best_day}</b> آية" if best_day > 0 else ""

    text = (
        f"🕌 <b>ختمة القرآن</b>\n{get_lines()}\n\n"
        f"<code>{bar}</code>  <b>{pct:.1f}%</b>\n\n"
        f"📖 آخر قراءة: سورة <b>{sura_name}</b> — آية <b>{k['last_ayah']}</b>\n"
        f"📈 <b>{total:,}</b> / {db.TOTAL_QURAN_AYAT:,} آية"
        + best_line
        + f"\n\n📅 تقدم اليوم: <b>{today}</b> / {goal} آية  (<b>{daily_pct}%</b>)\n"
        f"<code>{daily_bar}</code>"
        + streak_line
        + goal_badge
        + f"\n\n<i>{motivational}</i>"
    )

    owner = (uid, cid)
    buttons = [
        btn("▶️ متابعة القراءة",    "kh_continue",     {}, owner=owner, color=_G),
        btn("🎯 هدف يومي",          "kh_goal_panel",   {}, owner=owner, color=_B),
        btn("🔔 تذكير ختمتي",       "kh_rem_panel",    {}, owner=owner, color=_B),
        btn("🕌 ابدأ ختمة جديدة",   "kh_reset_prompt", {}, owner=owner, color=_R),
        btn("❌ إغلاق",             "kh_close",        {}, owner=owner, color=_R),
    ]
    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[1, 2, 2])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[1, 2, 2],
                owner_id=uid, reply_to=reply_to)
    _announce_achievements(uid, cid)


def _announce_achievements(uid, cid):
    try:
        for label in db.check_new_achievements(uid):
            bot.send_message(
                cid,
                f"🏆 <b>إنجاز جديد!</b>\n\n📖 <b>{label}</b>\n\n🔥 استمر في القراءة!",
                parse_mode="HTML",
            )
    except Exception:
        pass


@register_action("kh_continue")
def on_continue(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    k    = db.get_khatma(uid)
    ayah = db.get_ayah_by_sura_number(k["last_surah"], k["last_ayah"])
    if not ayah:
        ayah = db.get_first_ayah()
    if not ayah:
        bot.answer_callback_query(call.id, "❌ لا توجد آيات.", show_alert=True)
        return
    from modules.quran.tashkeel_pref import get_pref
    from modules.quran.surah_reader import _show_khatmah_ayah
    _show_khatmah_ayah(uid, cid, ayah, call=call, returned=True,
                       with_tashkeel=get_pref(uid, "khatma"))


@register_action("kh_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("kh_back_main")
def on_back_main(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    _show_khatmah_settings(cid, uid, call=call)



# ══════════════════════════════════════════
# Daily goal panel
# ══════════════════════════════════════════

@register_action("kh_goal_panel")
def on_goal_panel(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    current = db.get_khatma_goal(uid)
    avg     = db.get_daily_avg(uid, days=3)
    if avg >= 40:
        suggestion, level_label = max(40, round(avg / 10) * 10), "مستوى نشط"
    elif avg >= 20:
        suggestion, level_label = max(20, round(avg / 10) * 10), "مستوى متوسط"
    else:
        suggestion, level_label = 10, "مستوى مبتدئ"
    suggestion = max(10, min(100, suggestion))
    text = (
        f"🎯 <b>الهدف اليومي</b>\n{get_lines()}\n\n"
        f"هدفك الحالي: <b>{current}</b> آية\n\n"
        f"⚡ <b>اقتراح ذكي: {level_label} ({suggestion} آية)</b>\n"
        f"<i>بناءً على متوسط قراءتك الأخيرة</i>\n\nاختر هدفك اليومي:"
    )
    goal_btns = [
        btn(f"✔️ {v}" if v == current else str(v), "kh_set_goal", {"v": v}, owner=owner, color=_B)
        for v in _GOAL_VALUES
    ]
    extra = [
        btn(f"⚡ استخدام الاقتراح ({suggestion})", "kh_set_goal", {"v": suggestion}, owner=owner, color=_G),
        btn("🔙 رجوع", "kh_back_main", {}, owner=owner, color=_R),
    ]
    edit_ui(call, text=text, buttons=goal_btns + extra, layout=[5, 5, 1, 1])


@register_action("kh_set_goal")
def on_set_goal(call, data):
    uid   = call.from_user.id
    value = int(data.get("v", 10))
    db.set_khatma_goal(uid, value)
    bot.answer_callback_query(call.id, f"✅ تم تعيين هدفك اليومي: {value} آية", show_alert=True)
    on_goal_panel(call, data)


# ══════════════════════════════════════════
# Reset
# ══════════════════════════════════════════

@register_action("kh_reset_prompt")
def on_reset_prompt(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    owner    = (uid, cid)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text="🕌 <b>ابدأ ختمة جديدة</b>\n\nسيتم حذف كل تقدمك.\n⚠️ لا يمكن التراجع.\n\nهل أنت متأكد؟",
            buttons=[
                btn("✅ نعم، ابدأ من جديد", "kh_reset_confirm", {}, owner=owner, color=_R),
                btn("❌ إلغاء",             "kh_back_main",     {}, owner=owner, color=_G),
            ], layout=[2])


@register_action("kh_reset_confirm")
def on_reset_confirm(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    db.reset_khatma(uid)
    bot.answer_callback_query(call.id, "✅ تم بدء ختمة جديدة.", show_alert=True)
    _show_khatmah_settings(cid, uid, call=call)


# ══════════════════════════════════════════
# Reminder panel
# ══════════════════════════════════════════

@register_action("kh_rem_panel")
def on_rem_panel(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    bot.answer_callback_query(call.id)
    _show_reminder_panel(cid, uid, call=call)


def _show_reminder_panel(cid, uid, reply_to=None, call=None):
    reminders = db.get_khatma_reminders(uid)
    owner     = (uid, cid)
    stored_tz = get_user_tz(uid)
    tz_h      = stored_tz // 60 if stored_tz is not None else None
    tz_info   = f"\n🌍 توقيتك: <b>UTC{'+' if tz_h >= 0 else ''}{tz_h}</b>" if tz_h is not None else ""

    text = f"🔔 <b>تذكيرات الختمة</b>{tz_info}\n{get_lines()}\n\n"
    if reminders:
        text += "⏰ <b>تذكيراتك:</b>\n"
        for r in reminders:
            text += f"• {_fmt_hour(r['hour'])}:{r['minute']:02d}\n"
        text += "\n"
    else:
        text += "لا توجد تذكيرات نشطة.\n\n"
    text += f"الحد الأقصى: {_MAX_REMINDERS} تذكيرات."

    buttons = [
        btn(f"❌ {_fmt_hour(r['hour'])}:{r['minute']:02d}", "kh_rem_delete",
            {"rid": r["id"]}, owner=owner, color=_R)
        for r in reminders
    ]
    if len(reminders) < _MAX_REMINDERS:
        buttons.append(btn("➕ إضافة تذكير", "kh_rem_add", {}, owner=owner, color=_G))
    buttons.append(btn("✏️ تغيير توقيتي", "kh_edit_tz", {}, owner=owner, color=_B))
    buttons.append(btn("🔙 رجوع", "kh_back_main", {}, owner=owner, color=_R))

    del_count = len(reminders)
    layout = ([del_count] if del_count else []) + ([1] if len(reminders) < _MAX_REMINDERS else []) + [1, 1]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout, owner_id=uid, reply_to=reply_to)


@register_action("kh_rem_delete")
def on_rem_delete(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    db.delete_khatma_reminder(int(data["rid"]), uid)
    bot.answer_callback_query(call.id, "✅ تم حذف التذكير.", show_alert=True)
    _show_reminder_panel(cid, uid, call=call)


@register_action("kh_rem_add")
def on_rem_add(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    owner    = (uid, cid)
    bot.answer_callback_query(call.id)
    if not _can_pm(uid):
        from utils.helpers import send_private_access_panel
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        send_private_access_panel(cid, caption=(
            "⚠️ <b>لا يمكن إرسال التذكير</b>\n\n"
            "يجب فتح المحادثة مع البوت في الخاص أولاً\n"
            "حتى تتمكن من استلام التذكيرات."
        ))
        return
    hour_btns = [btn(_fmt_hour(h), "kh_rem_pick_hour", {"h": h}, owner=owner) for h in range(24)]
    hour_btns.append(btn("🔙 رجوع", "kh_rem_panel", {}, owner=owner, color=_R))
    edit_ui(call, text="⏰ <b>اختر الساعة</b> (بتوقيتك المحلي):", buttons=hour_btns, layout=[4, 4, 4, 4, 4, 4, 1])


@register_action("kh_rem_pick_hour")
def on_rem_pick_hour(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    h        = int(data["h"])
    owner    = (uid, cid)
    bot.answer_callback_query(call.id)

    # إذا كان التوقيت محفوظاً → الدقيقة تؤدي مباشرة لشاشة التأكيد
    stored_tz     = get_user_tz(uid)
    minute_action = "kh_rem_confirm_stored" if stored_tz is not None else "kh_rem_pick_tz"

    min_btns = [btn(f"{m:02d}", minute_action, {"h": h, "m": m}, owner=owner) for m in range(0, 60, 5)]
    min_btns.append(btn("🔙 رجوع", "kh_rem_add", {}, owner=owner, color=_R))
    edit_ui(call, text=f"⏰ الساعة: <b>{_fmt_hour(h)}</b>\n\nاختر الدقيقة:", buttons=min_btns, layout=[6, 6, 1])


@register_action("kh_rem_confirm_stored")
def on_rem_confirm_stored(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    h, m     = int(data["h"]), int(data["m"])
    owner    = (uid, cid)

    stored_tz = get_user_tz(uid)
    if stored_tz is None:
        bot.answer_callback_query(call.id)
        _show_kh_tz_picker(call, h, m, owner)
        return

    tz_h     = stored_tz // 60
    tz_label = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}"
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b>\n"
                f"🌍 التوقيت المحفوظ: <b>{tz_label}</b>\n\n"
                "هل تريد الحفظ بهذا التوقيت؟"
            ),
            buttons=[
                btn("✅ حفظ", "kh_rem_confirm",
                    {"h": h, "m": m, "tz": stored_tz}, owner=owner, color=_G),
                btn("✏️ تغيير التوقيت", "kh_rem_pick_tz",
                    {"h": h, "m": m}, owner=owner, color=_B),
                btn("🔙 رجوع", "kh_rem_pick_hour",
                    {"h": h}, owner=owner, color=_R),
            ],
            layout=[1, 1, 1])


@register_action("kh_rem_pick_tz")
def on_rem_pick_tz(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    h, m     = int(data["h"]), int(data["m"])
    owner    = (uid, cid)
    bot.answer_callback_query(call.id)
    _show_kh_tz_picker(call, h, m, owner)


def _show_kh_tz_picker(call, h, m, owner):
    tz_btns = [
        btn(f"UTC{'+' if o >= 0 else ''}{o}", "kh_rem_confirm", {"h": h, "m": m, "tz": o * 60}, owner=owner)
        for o in range(-12, 15)
    ]
    tz_btns.append(btn("🔙 رجوع", "kh_rem_pick_hour", {"h": h}, owner=owner, color=_R))
    edit_ui(call,
            text=f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b>\n\nاختر فارق توقيتك عن UTC\nمثال: السعودية/اليمن = UTC+3",
            buttons=tz_btns, layout=[3] * 9 + [1])


@register_action("kh_rem_confirm")
def on_rem_confirm(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    h, m, tz = int(data["h"]), int(data["m"]), int(data["tz"])
    owner    = (uid, cid)
    if db.count_khatma_reminders(uid) >= _MAX_REMINDERS:
        bot.answer_callback_query(call.id, f"❌ الحد الأقصى {_MAX_REMINDERS} تذكيرات.", show_alert=True)
        return
    # حفظ التوقيت للاستخدام المستقبلي
    set_user_tz(uid, tz)
    db.add_khatma_reminder(uid, h, m, tz)
    tz_h     = tz // 60
    tz_label = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}"
    bot.answer_callback_query(call.id, "✅ تم ضبط التذكير بنجاح!", show_alert=True)
    edit_ui(call,
            text=(
                f"✅ <b>تم ضبط التذكير بنجاح!</b>\n{get_lines()}\n\n"
                f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b> ({tz_label})\n\n"
                "ستصلك رسالة خاصة يومياً في هذا الوقت 🔔"
            ),
            buttons=[
                btn("📋 تذكيراتي",     "kh_rem_panel", {}, owner=owner, color=_B),
                btn("✏️ تغيير توقيتي", "kh_edit_tz",   {}, owner=owner, color=_B),
                btn("🔙 رجوع",         "kh_back_main", {}, owner=owner, color=_R),
            ], layout=[2, 1])


def _can_pm(user_id: int) -> bool:
    try:
        bot.send_chat_action(user_id, "typing")
        return True
    except Exception:
        return False


@register_action("kh_edit_tz")
def on_edit_tz(call, data):
    uid, cid = call.from_user.id, call.message.chat.id
    owner    = (uid, cid)
    bot.answer_callback_query(call.id)

    stored_tz = get_user_tz(uid)
    tz_h      = stored_tz // 60 if stored_tz is not None else 0
    tz_label  = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}" if stored_tz is not None else "غير محدد"

    tz_btns = [
        btn(f"UTC{'+' if o >= 0 else ''}{o}", "kh_save_tz",
            {"tz": o * 60}, owner=owner)
        for o in range(-12, 15)
    ]
    tz_btns.append(btn("🔙 رجوع", "kh_rem_panel", {}, owner=owner, color=_R))
    edit_ui(call,
            text=(
                f"🌍 <b>تعديل التوقيت</b>\n{get_lines()}\n\n"
                f"توقيتك الحالي: <b>{tz_label}</b>\n\n"
                "اختر توقيتك الجديد:"
            ),
            buttons=tz_btns,
            layout=[3] * 9 + [1])


@register_action("kh_save_tz")
def on_save_tz(call, data):
    uid   = call.from_user.id
    tz    = int(data["tz"])
    tz_h  = tz // 60
    set_user_tz(uid, tz)
    bot.answer_callback_query(call.id,
                              f"✅ تم حفظ التوقيت: UTC{'+' if tz_h >= 0 else ''}{tz_h}",
                              show_alert=True)
    _show_reminder_panel(call.message.chat.id, uid, call=call)

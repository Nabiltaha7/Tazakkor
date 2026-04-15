"""
دليل المطور التفاعلي — شرح كل ميزة يمكن للمطور إدارتها
"""
from core.bot import bot
from core.admin import is_any_dev
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines

_B  = "p"
_GR = "su"
_RD = "d"

# ══════════════════════════════════════════
# محتوى الأقسام
# ══════════════════════════════════════════

_SECTIONS = {
    "azkar_content": {
        "emoji": "📿",
        "title": "نظام الأذكار (المحتوى)",
        "pages": [
            {
                "title": "📿 نظام الأذكار — نظرة عامة",
                "content": (
                    "نظام الأذكار نوع محتوى مستقل مع دعم النشر التلقائي.\n\n"
                    "▶️ <b>أمر المستخدم:</b>\n"
                    "• <code>أذكار</code> — يعرض ذكراً عشوائياً\n"
                    "• <code>أذكار [رقم]</code> — يعرض ذكراً بمعرف محدد\n\n"
                    "⚙️ <b>التفعيل التلقائي (للمشرفين):</b>\n"
                    "• <code>تفعيل الأذكار</code> — يبدأ الإرسال التلقائي\n"
                    "• <code>إيقاف الأذكار</code> — يوقف الإرسال\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "• جدول <code>azkar</code> في <code>content_hub.db</code>\n"
                    "• عمود <code>azkar_enabled</code> في جدول <code>groups</code>\n\n"
                    "📌 <b>الملفات المعنية:</b>\n"
                    "• <code>modules/content_hub/azkar_sender.py</code> — المُرسِل التلقائي\n"
                    "• <code>modules/content_hub/hub_db.py</code> — تعريف الجدول\n"
                    "• <code>database/db_schema/groups.py</code> — عمود <code>azkar_enabled</code>\n"
                    "• <code>database/daily_tasks.py</code> — تسجيل <code>send_azkar</code>"
                ),
            },
            {
                "title": "📿 الفرق بين الأذكار والاقتباسات",
                "content": (
                    "📊 <b>مقارنة النظامين:</b>\n\n"
                    "💬 <b>الاقتباسات (quotes_sender):</b>\n"
                    "• جدول: <code>quotes</code> فقط\n"
                    "• عمود التفعيل: <code>quotes_enabled</code>\n"
                    "• الأمر: <code>تفعيل الاقتباسات</code> / <code>إيقاف الاقتباسات</code>\n"
                    "• الثابت: <code>quotes_interval_minutes</code>\n\n"
                    "📿 <b>الأذكار (azkar_sender):</b>\n"
                    "• جدول: <code>azkar</code> فقط\n"
                    "• عمود التفعيل: <code>azkar_enabled</code>\n"
                    "• الأمر: <code>تفعيل الأذكار</code> / <code>إيقاف الأذكار</code>\n"
                    "• الثابت: <code>azkar_interval_minutes</code>\n\n"
                    "⛔ <b>لا تُرسَل تلقائياً:</b>\n"
                    "anecdotes / stories / wisdom / poetry\n"
                    "هذه تُعرض بالأمر المباشر فقط.\n\n"
                    "📌 <b>إدارة المحتوى:</b>\n"
                    "<code>لوحة الإدارة</code> → 📚 إدارة المحتوى → 📿 أذكار\n"
                    "الجدول فارغ عند الإنشاء — يُملأ من لوحة المطور أو seed."
                ),
            },
        ],
    },

    "quran_khatmah": {
        "emoji": "📖",
        "title": "نظام القرآن والختمة",
        "pages": [
            {
                "title": "📖 أوامر القرآن — نظرة عامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/quran/quran_handler.py</code> — dispatcher الأوامر\n"
                    "• <code>modules/quran/khatmah.py</code> — منطق الختمة والإعدادات\n"
                    "• <code>modules/quran/surah_reader.py</code> — عرض الآيات والتنقل\n"
                    "• <code>modules/quran/quran_db.py</code> — طبقة قاعدة البيانات\n"
                    "• <code>modules/quran/quran_service.py</code> — منطق الأعمال\n"
                    "• <code>modules/quran/quran_ui.py</code> — بناء النصوص والأزرار\n\n"
                    "▶️ <b>أوامر المستخدم:</b>\n"
                    "• <code>ختمتي</code> — يعرض الآية التالية مباشرة\n"
                    "• <code>إعدادات ختمة</code> — لوحة الإحصائيات والإعدادات\n"
                    "• <code>تذكير ختمتي</code> — إعداد تذكيرات يومية\n"
                    "• <code>تلاوة</code> — استئناف التلاوة الحرة\n"
                    "• <code>قراءة سورة</code> — قراءة سورة بعينها\n"
                    "• <code>مفضلتي</code> — الآيات المحفوظة\n"
                    "• <code>آية [كلمة]</code> — بحث في القرآن\n\n"
                    "▶️ <b>أوامر المطور:</b>\n"
                    "• <code>إضافة آيات</code> — واجهة إضافة آيات\n"
                    "• <code>إضافة تفسير</code> — واجهة إضافة تفاسير\n"
                    "• <code>اضف آيات [سورة] [رقم]</code> — إضافة نصية مباشرة\n"
                    "• <code>عدل آية [id]</code> — تعديل نص آية\n"
                    "• <code>عدل تفسير [id]</code> — تعديل تفسير"
                ),
            },
            {
                "title": "🕌 ختمتي — التدفق التقني",
                "content": (
                    "📌 <b>الأمر الجديد:</b> <code>ختمتي</code>\n"
                    "يعرض الآية التالية مباشرة — بدون لوحة أو قوائم.\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ <code>handle_khatmah_read_command(message)</code>\n"
                    "2️⃣ <code>db.get_khatma(uid)</code> → last_surah + last_ayah\n"
                    "3️⃣ <code>db.get_ayah_by_sura_number(surah, ayah)</code>\n"
                    "4️⃣ <code>_show_khatmah_ayah(uid, cid, ayah)</code>\n"
                    "5️⃣ <code>db.update_khatma(uid, sura_id, ayah_number)</code>\n\n"
                    "📌 <b>الأمر الجديد:</b> <code>إعدادات ختمة</code>\n"
                    "يفتح لوحة الإحصائيات والإعدادات.\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ <code>handle_khatmah_settings_command(message)</code>\n"
                    "2️⃣ <code>_show_khatmah_settings(cid, uid)</code>\n\n"
                    "📌 <b>أزرار الإعدادات:</b>\n"
                    "• <code>kh_continue</code> → <code>_show_khatmah_ayah</code>\n"
                    "• <code>kh_goal_panel</code> → هدف يومي\n"
                    "• <code>kh_rem_panel</code> → تذكيرات\n"
                    "• <code>kh_reset_prompt</code> → إعادة ضبط\n\n"
                    "⚠️ <b>لا توجد قائمة سور في تدفق الختمة</b>\n"
                    "التنقل يعبر السور تلقائياً عبر <code>get_next_ayah(aid)</code>"
                ),
            },
            {
                "title": "🔘 أزرار القراءة — kh_next / kh_prev",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/quran/surah_reader.py</code>\n\n"
                    "🔄 <b>التنقل المتواصل:</b>\n"
                    "• <code>kh_next</code> → <code>db.get_next_ayah(aid)</code>\n"
                    "  يعبر السور تلقائياً — بدون قيد <code>sura_id</code>\n"
                    "• <code>kh_prev</code> → <code>db.get_prev_ayah(aid)</code>\n"
                    "  نفس المنطق للخلف\n\n"
                    "📌 <b>الدالة الرئيسية:</b>\n"
                    "<code>_show_khatmah_ayah(uid, cid, ayah, call, reply_to, returned)</code>\n\n"
                    "تقوم بـ:\n"
                    "1️⃣ <code>db.save_surah_read_progress(uid, sura_id, ayah_number)</code>\n"
                    "2️⃣ <code>db.update_khatma(uid, sura_id, ayah_number)</code>\n"
                    "3️⃣ بناء نص الآية مع اسم السورة + رقم الآية\n"
                    "4️⃣ أزرار: التالية، السابقة، تفسير، مفضلة، 🔙 ختمتي\n\n"
                    "📌 <b>أزرار التفسير والمفضلة:</b>\n"
                    "• <code>kh_tafseer</code> / <code>kh_show_tafseer</code>\n"
                    "• <code>kh_fav</code> — toggle المفضلة\n"
                    "• <code>kh_back_main</code> → <code>_show_khatmah_settings</code>"
                ),
            },
            {
                "title": "🗄 قاعدة بيانات الختمة",
                "content": (
                    "📌 <b>الجداول:</b>\n\n"
                    "• <code>khatma_progress</code>\n"
                    "  user_id, last_surah, last_ayah, total_read, updated_at\n\n"
                    "• <code>khatma_goals</code>\n"
                    "  user_id, daily_target\n\n"
                    "• <code>khatma_daily_log</code>\n"
                    "  user_id, log_date, count\n\n"
                    "• <code>khatma_streak</code>\n"
                    "  user_id, current_streak, last_read_date\n\n"
                    "• <code>khatma_reminders</code>\n"
                    "  id, user_id, hour, minute, tz_offset, enabled\n\n"
                    "• <code>khatma_counted_ayat</code>\n"
                    "  user_id, ayah_id, log_date — منع تكرار العد\n\n"
                    "📌 <b>الدوال الرئيسية في quran_db.py:</b>\n"
                    "• <code>get_khatma(uid)</code> — آخر موضع\n"
                    "• <code>update_khatma(uid, surah_id, ayah_number)</code>\n"
                    "• <code>reset_khatma(uid)</code> — إعادة من الفاتحة\n"
                    "• <code>get_streak(uid)</code> / <code>get_today_count(uid)</code>\n"
                    "• <code>get_due_khatma_reminders(utc_h, utc_m)</code>"
                ),
            },
        ],
    },

    "azkar": {
        "emoji": "📿",
        "title": "إدارة الأذكار",
        "pages": [
            {
                "title": "📿 إدارة الأذكار",
                "content": (
                    "📌 <b>الوصول (طريقتان):</b>\n"
                    "• <code>لوحة الإدارة</code> → 📿 إدارة الأذكار\n"
                    "• أو اكتب مباشرة: <code>إدارة الأذكار</code>\n\n"
                    "📋 <b>أنواع الأذكار (type):</b>\n"
                    "• <code>0</code> = 🌅 أذكار الصباح\n"
                    "• <code>1</code> = 🌙 أذكار المساء\n"
                    "• <code>2</code> = 😴 أذكار النوم\n"
                    "• <code>3</code> = ☀️ أذكار الاستيقاظ\n\n"
                    "🔧 <b>العمليات المتاحة:</b>\n"
                    "• عرض قائمة الأذكار لكل نوع\n"
                    "• ✏️ تعديل نص أي ذكر\n"
                    "• 🔢 تعديل عدد التكرار\n"
                    "• 🗑 حذف ذكر (المطور الأساسي فقط)\n"
                    "• ➕ إضافة ذكر جديد بالصيغة:\n"
                    "  <code>النص | عدد التكرار</code>\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "الأذكار محفوظة في <code>azkar.db</code> منفصلة عن باقي البيانات.\n"
                    "تقدم المستخدمين محفوظ في جدول <code>azkar_progress</code>.\n\n"
                    "📌 <b>تفعيل الأذكار التلقائية للمجموعة:</b>\n"
                    "• من لوحة <code>الأوامر</code> → 📿 الأذكار التلقائية (زر toggle)\n"
                    "• أو بالأمر: <code>تفعيل الأذكار</code> / <code>إيقاف الأذكار</code>\n"
                    "• العمود: <code>groups.azkar_enabled</code>\n"
                    "• الدالة: <code>toggle_azkar()</code> في <code>azkar_sender.py</code>\n"
                    "• أو عبر النظام العام: <code>toggle_feature(cid, 'azkar_enabled')</code>"
                ),
            },
            {
                "title": "📿 الأذكار — ميزات المستخدم",
                "content": (
                    "هذه الميزات للمستخدمين العاديين — ليست للإدارة.\n\n"
                    "▶️ <b>أوامر المستخدم:</b>\n"
                    "• <code>أذكار الصباح</code> 🌅\n"
                    "• <code>أذكار المساء</code> 🌙\n"
                    "• <code>أذكار النوم</code> 😴\n"
                    "• <code>أذكار الاستيقاظ</code> ☀️\n"
                    "• <code>ذكرني ذكري</code> — تذكير يومي تلقائي\n"
                    "• <code>ذكر</code> — ذكر مخصص مؤقت\n\n"
                    "🔄 <b>إعادة التعيين اليومية:</b>\n"
                    "تقدم كل مستخدم يُعاد تلقائياً في اليوم التالي.\n\n"
                    "⚠️ <b>ملاحظة للمطور:</b>\n"
                    "الأذكار والمجلة ميزتان مستقلتان تماماً.\n"
                    "الأذكار = محتوى ديني وتعبدي.\n"
                    "المجلة = أخبار وأحداث اللعبة."
                ),
            },
        ],
    },

    "channels_feature": {
        "emoji": "📡",
        "title": "ميزة القنوات",
        "pages": [
            {
                "title": "📡 البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/content_hub/channel_admin.py</code> — أوامر الربط/فك الربط\n"
                    "• <code>modules/content_hub/channel_sync.py</code> — استقبال المنشورات\n"
                    "• <code>modules/content_hub/hub_db.py</code> — قاعدة البيانات\n"
                    "• <code>main.py</code> — تسجيل handlers القنوات\n\n"
                    "📋 <b>جدول DB:</b>\n"
                    "<code>linked_channels</code> في <code>content_hub.db</code>\n"
                    "الحقول: channel_id, channel_name, content_type, linked_at\n\n"
                    "📂 <b>جداول المحتوى المستهدفة:</b>\n"
                    "quotes | anecdotes | stories | wisdom | poetry\n\n"
                    "🔑 <b>أوامر المطور:</b>\n"
                    "• <code>ربط قناة</code>\n"
                    "• <code>فك ربط قناة</code>\n"
                    "• <code>القنوات المرتبطة</code>"
                ),
            },
            {
                "title": "🔄 تدفق الربط — خطوة بخطوة",
                "content": (
                    "📌 <b>الملف:</b> <code>channel_admin.py</code>\n\n"
                    "1️⃣ <b>المطور يكتب</b> <code>ربط قناة</code>\n"
                    "   → <code>_start_link_flow()</code> تُعيّن state: <code>ch_link / await_channel</code>\n\n"
                    "2️⃣ <b>المطور يرسل معرف القناة</b> أو يعيد توجيه رسالة\n"
                    "   → <code>_process_channel_input()</code>\n"
                    "   → يتحقق أن البوت مشرف عبر <code>bot.get_chat_member()</code>\n"
                    "   → إذا فشل → رسالة خطأ واضحة + clear state\n\n"
                    "3️⃣ <b>يعرض أزرار نوع المحتوى</b>\n"
                    "   → quotes | stories | anecdotes | wisdom | poetry\n\n"
                    "4️⃣ <b>المطور يختار النوع</b>\n"
                    "   → callback <code>ch_select_type</code>\n"
                    "   → <code>link_channel(channel_id, content_type, name)</code>\n"
                    "   → INSERT OR UPDATE في <code>linked_channels</code>\n\n"
                    "✅ <b>النتيجة:</b> كل منشور جديد في القناة يُستورد تلقائياً."
                ),
            },
            {
                "title": "📥 استقبال المنشورات — channel_sync.py",
                "content": (
                    "📌 <b>التسجيل في main.py:</b>\n"
                    "<code>@bot.channel_post_handler(func=lambda m: True)\n"
                    "def on_channel_post(message):\n"
                    "    handle_channel_post(message)</code>\n\n"
                    "<code>@bot.edited_channel_post_handler(func=lambda m: True)\n"
                    "def on_channel_post_edit(message):\n"
                    "    handle_channel_post_edit(message)</code>\n\n"
                    "📌 <b>منطق handle_channel_post():</b>\n"
                    "1️⃣ <code>get_linked_channel(channel_id)</code> — هل القناة مرتبطة؟\n"
                    "2️⃣ استخراج النص: <code>message.text or message.caption</code>\n"
                    "3️⃣ <code>_clean(text)</code> — إزالة أسطر فارغة ومسافات زائدة\n"
                    "4️⃣ <code>insert_content(table, text)</code> — INSERT OR IGNORE\n\n"
                    "📌 <b>منطق handle_channel_post_edit():</b>\n"
                    "1️⃣ نفس الفحص\n"
                    "2️⃣ <code>upsert_content_by_text(old, new)</code>\n"
                    "3️⃣ إذا لم يجد النص القديم → يُدرج كمحتوى جديد\n\n"
                    "⚠️ <b>الوسائط بدون نص تُتجاهل تلقائياً.</b>"
                ),
            },
            {
                "title": "🗄️ دوال قاعدة البيانات",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/content_hub/hub_db.py</code>\n\n"
                    "🔗 <b>ربط قناة:</b>\n"
                    "<code>link_channel(channel_id, content_type, channel_name)\n"
                    "# INSERT OR UPDATE — آمن للاستدعاء مرتين</code>\n\n"
                    "❌ <b>فك الربط:</b>\n"
                    "<code>unlink_channel(channel_id) → bool</code>\n\n"
                    "🔍 <b>جلب قناة:</b>\n"
                    "<code>get_linked_channel(channel_id) → dict | None</code>\n\n"
                    "📋 <b>جلب الكل:</b>\n"
                    "<code>get_all_linked_channels() → list[dict]</code>\n\n"
                    "📝 <b>تحديث محتوى بالنص:</b>\n"
                    "<code>upsert_content_by_text(table, old_text, new_text) → bool</code>\n\n"
                    "📌 <b>INSERT OR IGNORE في insert_content():</b>\n"
                    "يمنع التكرار — نفس النص لا يُدرج مرتين."
                ),
            },
            {
                "title": "➕ إضافة نوع محتوى جديد",
                "content": (
                    "📌 <b>لإضافة نوع محتوى جديد (مثلاً: jokes):</b>\n\n"
                    "1️⃣ <b>في hub_db.py:</b>\n"
                    "<code>CONTENT_TYPES['نكتة'] = 'jokes'\n"
                    "TYPE_LABELS['jokes'] = '😂 نكتة'</code>\n"
                    "وأضف <code>'jokes'</code> في حلقة <code>create_tables()</code>\n\n"
                    "2️⃣ <b>في channel_admin.py:</b>\n"
                    "<code>_TYPE_BUTTONS.append(('😂 نكت', 'jokes'))</code>\n\n"
                    "3️⃣ <b>في hub_handler.py:</b>\n"
                    "أضف الأمر العربي في <code>CONTENT_TYPES</code> إذا أردت أمراً للمستخدم.\n\n"
                    "4️⃣ <b>في dev_control_panel.py:</b>\n"
                    "أضف زراً في <code>_show_content_hub_panel()</code>:\n"
                    "<code>btn('😂 نكت', 'hub_dev_type', {'type': 'jokes'}, ...)</code>\n\n"
                    "✅ <b>الجدول يُنشأ تلقائياً</b> عند أول استدعاء لـ <code>create_tables()</code>."
                ),
            },
        ],
    },

    "quran_systems": {
        "emoji": "📖",
        "title": "نظام القرآن",
        "pages": [
            {
                "title": "📖 الأنظمة + Streak + Dedup",
                "content": (
                    "📖 <b>التلاوة:</b> <code>user_quran_progress</code>\n"
                    "📚 <b>قراءة سورة:</b> <code>surah_read_progress</code>\n"
                    "🕌 <b>الختمة:</b> <code>khatma_progress</code>\n\n"
                    "🛡 <b>منع التكرار:</b>\n"
                    "<code>khatma_counted_ayat(user_id, ayah_id, log_date)</code>\n"
                    "كل آية تُحسب مرة واحدة يومياً فقط.\n\n"
                    "🔥 <b>Streak — سماحية 7 أيام:</b>\n"
                    "• gap == 0 → نفس اليوم، لا تغيير\n"
                    "• gap == 1 → streak + 1\n"
                    "• gap ≤ 7 → streak + 1 (grace period)\n"
                    "• gap > 7 → reset to 1\n\n"
                    "🏆 <b>الإنجازات:</b>\n"
                    "<code>khatma_achievements_seen(user_id, key)</code>\n"
                    "• total_read ≥ 1000 → قارئ نشيط\n"
                    "• streak ≥ 7 → أسبوع متواصل\n"
                    "تُعلَن مرة واحدة فقط."
                ),
            },
            {
                "title": "🔔 تذكيرات + التذاكر",
                "content": (
                    "🔔 <b>تذكيرات الختمة:</b>\n"
                    "<code>khatma_reminders</code> — max 2\n"
                    "المُجدوِل: <code>khatmah_reminder.py</code>\n"
                    "Silent fail إذا حجب المستخدم البوت.\n\n"
                    "📱 <b>شرط الخاص:</b>\n"
                    "<code>bot.send_chat_action(uid, 'typing')</code>\n"
                    "إذا فشل → <code>send_private_access_panel()</code>\n\n"
                    "🎫 <b>التذاكر — نص فقط:</b>\n"
                    "في <code>handle_ticket_message_input()</code>:\n"
                    "<code>if not message.text: → رفض + رسالة واضحة</code>\n"
                    "الصور والملصقات والملفات مرفوضة.\n"
                    "لا crash — يُرجع True ويُعلم المستخدم."
                ),
            },
        ],
    },

}


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def open_dev_guide(message):
    """يفتح دليل المطور — للمطورين فقط"""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_any_dev(user_id):
        bot.reply_to(message, "❌ هذا الدليل للمطورين فقط.")
        return

    _send_guide_menu(chat_id, user_id)


def _send_guide_menu(chat_id, user_id):
    owner = (user_id, chat_id)
    text  = (
        "📚 <b>دليل المطور التفاعلي</b>\n"
        f"{get_lines()}\n\n"
        "اختر القسم الذي تريد شرحه:"
    )
    buttons = [
        btn(f"{s['emoji']} {s['title']}", "devguide_section",
            data={"sid": sid, "p": 0}, owner=owner, color=_B)
        for sid, s in _SECTIONS.items()
    ]
    buttons.append(btn("❌ إخفاء", "devguide_hide", owner=owner, color=_RD))

    layout = _grid(len(buttons) - 1, 2) + [1]
    send_ui(chat_id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


def _page_buttons(action: str, extra: dict, total: int, current: int, owner: tuple) -> tuple:
    """
    Builds numbered page buttons (1-based display, 0-based index).
    Returns (buttons_list, layout_list). 4 per row.
    Current page uses 'success' style; all others use default 'primary'.
    """
    page_btns = []
    for i in range(total):
        color = _GR if i == current else _B
        page_btns.append(btn(str(i + 1), action, {**extra, "p": i}, owner=owner, color=color))

    rows = []
    for i in range(0, len(page_btns), 4):
        rows.append(page_btns[i:i + 4])

    layout = [len(r) for r in rows]
    return [b for r in rows for b in r], layout


@register_action("devguide_section")
def show_section(call, data):
    sid   = data.get("sid")
    page  = int(data.get("p", 0))
    owner = (call.from_user.id, call.message.chat.id)

    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    section = _SECTIONS.get(sid)
    if not section:
        bot.answer_callback_query(call.id, "❌ القسم غير موجود", show_alert=True)
        return

    pages = section["pages"]
    total = len(pages)
    page  = max(0, min(page, total - 1))
    pg    = pages[page]

    text = (
        f"{section['emoji']} <b>{section['title']}</b>\n"
        f"{get_lines()}\n\n"
        f"📋 <b>{pg['title']}</b>\n"
        f"{get_lines()}\n\n"
        f"{pg['content']}"
    )
    if total > 1:
        text += f"\n\n📄 صفحة {page + 1} / {total}"

    pg_btns, pg_layout = _page_buttons("devguide_section", {"sid": sid}, total, page, owner)

    buttons = pg_btns + [
        btn("🔙 القائمة الرئيسية", "devguide_back", owner=owner, color=_RD),
    ]
    layout = pg_layout + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("devguide_back")
def back_to_guide_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        return

    owner = (user_id, chat_id)
    text  = (
        "📚 <b>دليل المطور التفاعلي</b>\n"
        f"{get_lines()}\n\n"
        "اختر القسم الذي تريد شرحه:"
    )
    buttons = [
        btn(f"{s['emoji']} {s['title']}", "devguide_section",
            data={"sid": sid, "p": 0}, owner=owner, color=_B)
        for sid, s in _SECTIONS.items()
    ]
    buttons.append(btn("❌ إخفاء", "devguide_hide", owner=owner, color=_RD))
    layout = _grid(len(buttons) - 1, 2) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("devguide_hide")
def hide_guide(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


def _grid(n: int, cols: int = 2) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]

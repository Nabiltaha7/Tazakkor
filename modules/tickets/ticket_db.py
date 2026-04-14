"""
modules/tickets/ticket_db.py
──────────────────────────────
Backward-compatible shim — يُحوِّل جميع الاستدعاءات إلى
database/db_queries/reports_queries.py

الكود الجديد يجب أن يستورد مباشرةً من:
    from database.db_queries.reports_queries import ...
"""
from database.db_queries.reports_queries import (
    # جداول — لا تزال تُنشأ عبر init_db
    # التذاكر
    create_ticket,
    get_ticket,
    get_user_tickets,
    count_user_tickets,
    get_open_ticket_for_user,
    get_tickets_paginated,
    count_tickets,
    close_ticket,
    set_ticket_group_msg,
    get_ticket_by_group_msg,
    # رسائل التذاكر
    add_ticket_message,
    get_ticket_messages,
    # الحدود
    check_ticket_limits   as check_limits,
    record_ticket_usage,
    DAILY_TICKET_LIMIT    as DAILY_LIMIT,
    TICKET_COOLDOWN_SEC   as COOLDOWN_SEC,
    # الإحصائيات
    get_ticket_stats      as get_stats,
    # الحظر
    ban_ticket_user,
    unban_ticket_user,
    is_ticket_banned,
    get_banned_users_paginated,
    count_banned_users,
)


def create_ticket_tables():
    """No-op — tables are created by database.init_db.init_db()."""
    pass

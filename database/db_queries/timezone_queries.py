"""
database/db_queries/timezone_queries.py
─────────────────────────────────────────
Backward-compatible shim — يُحوِّل الاستدعاءات القديمة إلى users_queries.

الكود الجديد يجب أن يستخدم:
    from database.db_queries.users_queries import get_user_tz, set_user_tz
"""
from database.db_queries.users_queries import get_user_tz, set_user_tz

__all__ = ["get_user_tz", "set_user_tz"]

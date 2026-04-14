"""
modules/content_hub/hub_db.py
───────────────────────────────
Backward-compatible shim — يُحوِّل استدعاءات azkar_content إلى
database/db_queries/azkar_queries.py

الكود الجديد يجب أن يستورد مباشرةً من:
    from database.db_queries.azkar_queries import ...
"""
from database.db_queries.azkar_queries import (
    get_random_azkar_content  as get_random,
    get_azkar_content_by_id   as get_by_id,
    count_azkar_content       as count_rows,
    insert_azkar_content      as insert_content,
    update_azkar_content      as update_content,
    delete_azkar_content      as delete_content,
)

# ── ثوابت متبقية يستخدمها azkar_sender ──────────────────────────
TYPE_LABELS = {"azkar_content": "📿 ذكر"}


def create_tables() -> None:
    """No-op — table is created by database.init_db.init_db()."""
    pass

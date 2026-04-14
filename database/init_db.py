"""
database/init_db.py
────────────────────
Central database initializer for Tazakkor.

Creates all tables in FK-safe order, then seeds default data.

Table creation order (respects foreign key dependencies):
  1. users_tables    — users, user_timezone          (no dependencies)
  2. groups_tables   — groups                            (→ users)
  3. azkar_tables    — azkar, azkar_progress,
                       azkar_reminders, azkar_content (→ users)
  4. quran_tables    — suras, ayat, khatma_*,
                       user_quran_progress, ...       (→ users)
  5. reports_tables  — bot_constants, bot_developers,
                       tickets, ticket_*              (→ users)
"""
from database.db_scheme.users_tables   import create_users_tables
from database.db_scheme.groups_tables  import create_groups_tables
from database.db_scheme.azkar_tables   import create_azkar_tables
from database.db_scheme.quran_tables   import create_quran_tables
from database.db_scheme.reports_tables import create_reports_tables, _seed_developers


def init_db() -> None:
    """
    Creates all database tables in FK-safe order.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    """
    create_users_tables()
    create_groups_tables()
    create_azkar_tables()
    create_quran_tables()
    create_reports_tables()

    print("✅ [Tazakkor] All database tables created.")

    _seed_defaults()


def _seed_defaults() -> None:
    """Seeds default data after table creation."""

    # Seed default developers and bot_constants
    try:
        _seed_developers()
    except Exception as e:
        print(f"[init_db] warning — seed_developers: {e}")

    # Seed default azkar content
    # Imported lazily to avoid circular dependency:
    #   database → modules → database
    try:
        from modules.azkar.seed_azkar import seed as _seed_azkar
        _seed_azkar()
    except Exception as e:
        print(f"[init_db] warning — seed_azkar: {e}")

-- ═══════════════════════════════════════════════════════════════════════════
-- Tazakkor Bot — Supabase PostgreSQL Migration Script
-- Run this once in Supabase SQL Editor to create all tables.
-- The bot's init_db() also runs CREATE TABLE IF NOT EXISTS on startup,
-- so this script is provided as a reference and for manual setup.
-- ═══════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────
-- 1. users
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id       SERIAL  PRIMARY KEY,
    user_id  BIGINT  NOT NULL UNIQUE,
    name     TEXT    NOT NULL DEFAULT '',
    username TEXT    DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- ─────────────────────────────────────────────
-- 2. user_timezone
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_timezone (
    id         SERIAL  PRIMARY KEY,
    user_id    BIGINT  NOT NULL UNIQUE,
    tz_offset  INTEGER NOT NULL DEFAULT 0,
    updated_at BIGINT  DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ─────────────────────────────────────────────
-- 3. groups
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS groups (
    id                 SERIAL  PRIMARY KEY,
    group_id           BIGINT  NOT NULL UNIQUE,
    name               TEXT    NOT NULL DEFAULT 'Unknown',
    joined_at          BIGINT  NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    tz_offset          INTEGER NOT NULL DEFAULT 180,
    azkar_enabled      INTEGER NOT NULL DEFAULT 1,
    azkar_interval     INTEGER NOT NULL DEFAULT 15,
    azkar_rem_morning  INTEGER DEFAULT NULL,
    azkar_rem_evening  INTEGER DEFAULT NULL,
    azkar_rem_sleep    INTEGER DEFAULT NULL,
    azkar_rem_wakeup   INTEGER DEFAULT NULL
);

-- ─────────────────────────────────────────────
-- 4. azkar
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS azkar (
    id           SERIAL  PRIMARY KEY,
    text         TEXT    NOT NULL,
    repeat_count INTEGER NOT NULL DEFAULT 1,
    zikr_type    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_azkar_type ON azkar(zikr_type);

-- ─────────────────────────────────────────────
-- 5. azkar_progress
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS azkar_progress (
    id         SERIAL  PRIMARY KEY,
    user_id    BIGINT  NOT NULL,
    zikr_type  INTEGER NOT NULL,
    zikr_index INTEGER NOT NULL DEFAULT 0,
    remaining  INTEGER NOT NULL DEFAULT -1,
    UNIQUE (user_id, zikr_type),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ─────────────────────────────────────────────
-- 6. azkar_reminders
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS azkar_reminders (
    id         SERIAL  PRIMARY KEY,
    user_id    BIGINT  NOT NULL,
    azkar_type INTEGER NOT NULL,
    hour       INTEGER NOT NULL,
    minute     INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT NOW()::TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_azkar_reminders_user ON azkar_reminders(user_id);

-- ─────────────────────────────────────────────
-- 7. azkar_content
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS azkar_content (
    id      SERIAL PRIMARY KEY,
    content TEXT   NOT NULL UNIQUE
);

-- ─────────────────────────────────────────────
-- 8. suras
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suras (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

-- ─────────────────────────────────────────────
-- 9. ayat
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ayat (
    id                    SERIAL  PRIMARY KEY,
    sura_id               INTEGER NOT NULL,
    ayah_number           INTEGER NOT NULL,
    text_with_tashkeel    TEXT    NOT NULL,
    text_without_tashkeel TEXT    NOT NULL,
    tafseer_mukhtasar     TEXT    DEFAULT NULL,
    tafseer_saadi         TEXT    DEFAULT NULL,
    tafseer_muyassar      TEXT    DEFAULT NULL,
    UNIQUE (sura_id, ayah_number),
    FOREIGN KEY (sura_id) REFERENCES suras(id)
);
CREATE INDEX IF NOT EXISTS idx_ayat_sura   ON ayat(sura_id);
CREATE INDEX IF NOT EXISTS idx_ayat_search ON ayat(text_without_tashkeel);

-- ─────────────────────────────────────────────
-- 10. user_quran_progress
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_quran_progress (
    user_id      BIGINT  PRIMARY KEY,
    last_ayah_id INTEGER NOT NULL DEFAULT 1,
    message_id   INTEGER DEFAULT NULL
);

-- ─────────────────────────────────────────────
-- 11. user_favorites
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_favorites (
    user_id  BIGINT  NOT NULL,
    ayah_id  INTEGER NOT NULL,
    added_at BIGINT  DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    PRIMARY KEY (user_id, ayah_id),
    FOREIGN KEY (ayah_id) REFERENCES ayat(id)
);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id);

-- ─────────────────────────────────────────────
-- 12. surah_read_progress
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS surah_read_progress (
    user_id  BIGINT  NOT NULL,
    surah_id INTEGER NOT NULL,
    ayah     INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, surah_id)
);
CREATE INDEX IF NOT EXISTS idx_surah_progress_user ON surah_read_progress(user_id);

-- ─────────────────────────────────────────────
-- 13. khatma_progress
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_progress (
    user_id    BIGINT    PRIMARY KEY,
    last_surah INTEGER   NOT NULL DEFAULT 1,
    last_ayah  INTEGER   NOT NULL DEFAULT 1,
    total_read INTEGER   NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- 14. khatma_goals
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_goals (
    user_id      BIGINT  PRIMARY KEY,
    daily_target INTEGER NOT NULL DEFAULT 10
);

-- ─────────────────────────────────────────────
-- 15. khatma_daily_log
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_daily_log (
    user_id  BIGINT  NOT NULL,
    log_date TEXT    NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, log_date)
);

-- ─────────────────────────────────────────────
-- 16. khatma_streak
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_streak (
    user_id        BIGINT  PRIMARY KEY,
    current_streak INTEGER NOT NULL DEFAULT 0,
    last_read_date TEXT
);

-- ─────────────────────────────────────────────
-- 17. khatma_reminders
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_reminders (
    id        SERIAL  PRIMARY KEY,
    user_id   BIGINT  NOT NULL,
    hour      INTEGER NOT NULL,
    minute    INTEGER NOT NULL,
    tz_offset INTEGER NOT NULL DEFAULT 0,
    enabled   INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_khatma_reminders_user ON khatma_reminders(user_id);

-- ─────────────────────────────────────────────
-- 18. khatma_counted_ayat
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_counted_ayat (
    user_id  BIGINT  NOT NULL,
    ayah_id  INTEGER NOT NULL,
    log_date TEXT    NOT NULL,
    PRIMARY KEY (user_id, ayah_id, log_date)
);

-- ─────────────────────────────────────────────
-- 19. khatma_achievements_seen
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS khatma_achievements_seen (
    user_id BIGINT NOT NULL,
    key     TEXT   NOT NULL,
    PRIMARY KEY (user_id, key)
);

-- ─────────────────────────────────────────────
-- 20. bot_constants
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_constants (
    name        TEXT   PRIMARY KEY,
    value       TEXT   NOT NULL,
    description TEXT   DEFAULT '',
    updated_at  BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER
);

-- ─────────────────────────────────────────────
-- 21. bot_developers
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_developers (
    id       SERIAL PRIMARY KEY,
    user_id  BIGINT NOT NULL UNIQUE,
    role     TEXT   NOT NULL DEFAULT 'secondary',
    added_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ─────────────────────────────────────────────
-- 22. tickets
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tickets (
    id               SERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL,
    chat_id          BIGINT NOT NULL,
    category         TEXT   NOT NULL,
    status           TEXT   NOT NULL DEFAULT 'open',
    dev_group_msg_id BIGINT DEFAULT NULL,
    created_at       BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);

-- ─────────────────────────────────────────────
-- 23. ticket_messages
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_messages (
    id             SERIAL  PRIMARY KEY,
    ticket_id      INTEGER NOT NULL,
    sender         TEXT    NOT NULL,
    message_id     BIGINT  DEFAULT NULL,
    message_type   TEXT    NOT NULL DEFAULT 'text',
    content        TEXT    DEFAULT NULL,
    file_id        TEXT    DEFAULT NULL,
    file_unique_id TEXT    DEFAULT NULL,
    created_at     BIGINT  DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
CREATE INDEX IF NOT EXISTS idx_ticket_messages ON ticket_messages(ticket_id);

-- ─────────────────────────────────────────────
-- 24. ticket_limits
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_limits (
    user_id   BIGINT  NOT NULL,
    date      TEXT    NOT NULL,
    count     INTEGER NOT NULL DEFAULT 0,
    last_used BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- ─────────────────────────────────────────────
-- 25. ticket_bans
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_bans (
    user_id   BIGINT PRIMARY KEY,
    banned_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER,
    reason    TEXT   DEFAULT NULL
);

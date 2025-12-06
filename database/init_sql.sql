-- ========================================
--  Table 1. users
--  玩家帳號、登入狀態、所在房間
-- ========================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,                        -- 使用者名稱
    password_hash TEXT NOT NULL,                      -- 雜湊密碼
    is_logged_in INTEGER DEFAULT 0,                   -- 登入狀態 (0=離線, 1=在線)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,        -- 建立時間
    last_login_at TEXT                               -- 最後登入時間
);

CREATE TABLE IF NOT EXISTS dev_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,                        -- 使用者名稱
    password_hash TEXT NOT NULL,                      -- 雜湊密碼
    is_logged_in INTEGER DEFAULT 0,                   -- 登入狀態 (0=離線, 1=在線)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,        -- 建立時間
    last_login_at TEXT                               -- 最後登入時間
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dev_user_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,           -- cli / gui / multi
    max_players INTEGER NOT NULL,
    current_version TEXT,              -- 最新版本
    entry_server TEXT,                 -- 啟動 server 指令
    entry_client TEXT,                 -- 啟動 client 指令
    short_desc TEXT,
    visible INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (dev_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS game_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
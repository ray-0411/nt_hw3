import sqlite3
import hashlib
from datetime import datetime
import uuid
import os
import json


DB_PATH = "data.db"
INIT_SQL_FILE = os.path.join(os.path.dirname(__file__), "init_sql.sql")

#part1:初始化資料庫連線與結構

def get_conn():
    """建立 SQLite 連線（自動關閉 thread 限制）"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """讀取 init_sql.sql 並初始化資料庫"""
    with open(INIT_SQL_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    with get_conn() as conn:
        conn.executescript(sql_script)
        conn.commit()
    print("✅ Database initialized from init_sql.sql")

#part2:users操作函式

def hash_password(password: str) -> str:
    """用 SHA256 雜湊密碼"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

#use
def lobby_init():
    """Lobby 初始化時呼叫：重設所有使用者登入狀態"""
    with get_conn() as conn:
        
        cur = conn.cursor()
        # 1️⃣ 全部使用者登出
        cur.execute("UPDATE users SET is_logged_in=0")
        
        conn.commit()
    
    print("🧹 Lobby Init: 所有使用者已標記為離線。")
    return {"ok": True, "msg": "All users reset to offline."}


def create_user(name: str, password: str):
    """註冊新使用者（註冊後自動登入）"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, password_hash, is_logged_in, last_login_at) VALUES (?, ?, 1, datetime('now'))",
                (name, hash_password(password)),
            )
            conn.commit()
            user_id = cur.lastrowid
        return {"ok": True, "id": user_id, "msg": f"User '{name}' created & logged in."}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"Username '{name}' already exists."}

#use
def login_user(name: str, password: str):
    """登入使用者"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, is_logged_in FROM users WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "User not found."}

        user_id, pw_hash, is_logged_in = row
        if pw_hash != hash_password(password):
            return {"ok": False, "error": "Invalid password."}

        # ✅ 檢查是否已登入
        if is_logged_in:
            return {"ok": False, "error": "User already logged in elsewhere."}

        # 更新登入狀態
        cur.execute(
            "UPDATE users SET is_logged_in=1, last_login_at=? WHERE id=?",
            (datetime.now().isoformat(), user_id),
        )
        conn.commit()
        return {"ok": True, "id": user_id, "name": name}

#use
def logout_user(user_id: int):
    """登出使用者"""
    with get_conn() as conn:
        cur = conn.cursor()
        # 取出使用者名稱
        cur.execute("SELECT name FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        username = row[0] if row else None

        # 更新狀態
        cur.execute(
            "UPDATE users SET is_logged_in=0 WHERE id=?",
            (user_id,),
        )
        conn.commit()

    print(f"🗂 使用者登出: id={user_id}, name={username}")
    return {"ok": True, "id": user_id, "name": username, "msg": "User logged out."}

#use
def get_online_users():
    """查詢所有在線使用者"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE is_logged_in=1 ORDER BY id")
        return cur.fetchall()

#use
def dev_lobby_init():
    """Lobby 初始化時呼叫：重設所有使用者登入狀態"""
    with get_conn() as conn:
        
        cur = conn.cursor()
        # 1️⃣ 全部使用者登出
        cur.execute("UPDATE dev_users SET is_logged_in=0")
        
        conn.commit()
    
    print("🧹 Dev Lobby Init: 所有使用者已標記為離線。")
    return {"ok": True, "msg": "All users reset to offline."}

def dev_create_user(name: str, password: str):
    """註冊新使用者（註冊後自動登入）"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dev_users (name, password_hash, is_logged_in, last_login_at) VALUES (?, ?, 1, datetime('now'))",
                (name, hash_password(password)),
            )
            conn.commit()
            user_id = cur.lastrowid
        return {"ok": True, "id": user_id, "msg": f"User '{name}' created & logged in."}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"Username '{name}' already exists."}


#use
def dev_login_user(name: str, password: str):
    """登入使用者"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, is_logged_in FROM dev_users WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "User not found."}

        user_id, pw_hash, is_logged_in = row
        if pw_hash != hash_password(password):
            return {"ok": False, "error": "Invalid password."}

        # ✅ 檢查是否已登入
        if is_logged_in:
            return {"ok": False, "error": "User already logged in elsewhere."}

        # 更新登入狀態
        cur.execute(
            "UPDATE dev_users SET is_logged_in=1, last_login_at=? WHERE id=?",
            (datetime.now().isoformat(), user_id),
        )
        conn.commit()
        return {"ok": True, "id": user_id, "name": name}

#use
def dev_logout_user(user_id: int):
    """登出使用者"""
    with get_conn() as conn:
        cur = conn.cursor()
        # 取出使用者名稱
        cur.execute("SELECT name FROM dev_users WHERE id=?", (user_id,))
        row = cur.fetchone()
        username = row[0] if row else None

        # 更新狀態
        cur.execute(
            "UPDATE dev_users SET is_logged_in=0 WHERE id=?",
            (user_id,),
        )
        conn.commit()

    print(f"🗂 使用者登出: id={user_id}, name={username}")
    return {"ok": True, "id": user_id, "name": username, "msg": "User logged out."}

def dev_create_game(data: dict):
    """建立新遊戲記錄"""
    name = data.get("game_name", "Unnamed Game")
    config = data.get("config", "{}")
    json_config = json.loads(config)
    dev_user_id = data.get("user_id", None)
    game_type = json_config.get("game_type", "unknown")
    max_players = json_config.get("max_players", 1)
    current_version = json_config.get("version", "1.0.0")
    entry_server = json_config.get("entry_server", "game_server.py")
    entry_client = json_config.get("entry_client", "game_client.py")
    short_desc = json_config.get("description", "")
    
    
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO games 
                (dev_user_id, name, game_type, 
                max_players, current_version, 
                entry_server, entry_client, 
                short_desc, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (dev_user_id, name, game_type, 
                max_players, current_version, 
                entry_server, entry_client, short_desc)
            )
            conn.commit()
            game_id = cur.lastrowid
        print(f"🎮 新遊戲建立: id={game_id}, name={data['game_name']}, by user_id={data['user_id']}")
        return {"ok": True, "game_id": game_id, "msg": f"Game '{data['game_name']}' created."}
    except Exception as e:
        print("❌ dev_create_game error:", e)
        return {"ok": False, "error": str(e)}

def dev_get_my_games(user_id: int):
    
    """取得使用者的遊戲列表"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, visible FROM games WHERE dev_user_id=? ORDER BY id",
                (user_id,)
            )
            rows = cur.fetchall()
            games = []
            for row in rows:
                games.append({
                    "id": row[0],
                    "name": row[1],
                    "visible": row[2],
                })
        return {"ok": True, "games": games}
    except Exception as e:
        print("❌ dev_get_my_games error:", e)
        return {"ok": False, "error": str(e)}
    

def dev_change_game_status(game_id: int, new_status: str):
    """更新遊戲狀態"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE games SET visible=?, updated_at=datetime('now') WHERE id=?",
                (new_status, game_id)
            )
            conn.commit()
        print(f"🛠 遊戲狀態更新: id={game_id}, new_status={new_status}")
        return {"ok": True, "msg": f"Game id={game_id} status updated to '{new_status}'."}
    except Exception as e:
        print("❌ dev_update_game_status error:", e)
        return {"ok": False, "error": str(e)}

def dev_update_game(data: dict):
    
    """建立新遊戲記錄"""
    game_id = data.get("game_id")
    name = data.get("game_name", "Unnamed Game")
    config = data.get("config", "{}")
    json_config = json.loads(config)
    dev_user_id = data.get("user_id", None)
    game_type = json_config.get("game_type", "unknown")
    max_players = json_config.get("max_players", 1)
    current_version = json_config.get("version", "1.0.0")
    entry_server = json_config.get("entry_server", "game_server.py")
    entry_client = json_config.get("entry_client", "game_client.py")
    short_desc = json_config.get("description", "")
    
    print("🛠 更新遊戲資料: ", data)
    
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE games SET 
                name=?, game_type=?, 
                max_players=?, current_version=?, 
                entry_server=?, entry_client=?, 
                short_desc=?, updated_at=datetime('now')
                WHERE id=? AND dev_user_id=?""",
                (name, game_type, 
                max_players, current_version, 
                entry_server, entry_client, 
                short_desc, game_id, dev_user_id)
            )
            conn.commit()
        print(f"🛠 遊戲更新: id={game_id}, name={name}, by user_id={dev_user_id}")
        return {"ok": True, "msg": f"Game id={game_id} updated."}
    except Exception as e:
        print("❌ dev_update_game error:", e)
        return {"ok": False, "error": str(e)}
    
def get_game_list():
    
    """取得所有可見的遊戲列表"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    g.id,
                    g.name,
                    g.game_type,
                    g.max_players,
                    g.current_version,
                    g.short_desc,
                    IFNULL(AVG(r.rating), 0) AS avg_rating,
                    COUNT(r.id) AS review_count
                FROM games g
                LEFT JOIN game_reviews r
                    ON g.id = r.game_id
                WHERE g.visible = 1
                GROUP BY g.id
                ORDER BY g.id
                """
            )
            rows = cur.fetchall()
            
            games = []
            for row in rows:
                games.append({
                    "id": row[0],
                    "name": row[1],
                    "game_type": row[2],
                    "max_players": row[3],
                    "current_version": row[4],
                    "short_desc": row[5],
                    "avg_rating": round(row[6], 2),   # 平均評分
                    "review_count": row[7],           # 評論數量
                })
                
        print("✅ 取得遊戲列表成功")
        return {"ok": True, "games": games}
    except Exception as e:
        print("❌ get_game_list error:", e)
        return {"ok": False, "error": str(e)}

def get_game_version(game_id: int):
    """取得指定遊戲的目前版本"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT current_version FROM games WHERE id=?",
                (game_id,)
            )
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "Game not found."}
            current_version = row[0]
        print(f"✅ 取得遊戲版本成功: game_id={game_id}, version={current_version}")
        return {"ok": True, "current_version": current_version}
    except Exception as e:
        print("❌ get_game_version error:", e)
        return {"ok": False, "error": str(e)}
    
def get_game_name_by_id(game_id: int):
    
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM games WHERE id=?",
                (game_id,)
            )
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "Game not found."}
            game_name = row[0]
        print(f"✅ 取得遊戲名稱成功: game_id={game_id}, name={game_name}")
        return {"ok": True, "game_name": game_name}
    except Exception as e:
        print("❌ get_game_name_by_id error:", e)
        return {"ok": False, "error": str(e)}


def grading(data: dict):
    user_id = data.get("user_id")
    game_id = data.get("game_id")
    score = data.get("score")
    comment = data.get("comment", "")
    
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO game_reviews 
                (user_id, game_id, rating, comment, created_at) 
                VALUES (?, ?, ?, ?, datetime('now'))""",
                (user_id, game_id, score, comment)
            )
            conn.commit()
        print(f"✅ 遊戲評分成功: user_id={user_id}, game_id={game_id}, score={score}")
        return {"ok": True, "msg": "Grading submitted."}
    except Exception as e:
        print("❌ grading error:", e)
        return {"ok": False, "error": str(e)}
    
    
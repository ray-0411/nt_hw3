import asyncio
import logging
from common.network import send_msg, recv_msg
import socket
import subprocess
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# -------------------------------
# 設定區
# -------------------------------
DB_HOST = "127.0.0.1"       # DB Server 位址
DB_PORT = 14411              # DB Server 監聽埠

connected_users = {}

def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 不需要真的連上網，這行只是讓 OS 幫我們找出出口介面 IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOBBY_HOST = get_host_ip()     # Lobby Server 對外開放 IP
LOBBY_PORT = 18110           # Lobby Server 監聽埠
db_reader = None
db_writer = None

def find_free_port(start=16800, end=16900):
    import socket
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((LOBBY_HOST, port))
                s.listen(1)  # 確保真的能 listen
                return port
            except OSError:
                continue
    raise RuntimeError("❌ 沒有可用的 port")



# -------------------------------
# 與 DB Server 溝通
# -------------------------------
async def db_request(req: dict):
    """透過既有的持續 TCP 連線與 DB Server 溝通"""
    global db_reader, db_writer
    try:
        await send_msg(db_writer, req)
        resp = await recv_msg(db_reader)
        return resp
    except Exception as e:
        print(f"⚠️ DB Server 通訊錯誤: {e}")
        return {"ok": False, "error": str(e)}


# -------------------------------
# 輔助函式
# -------------------------------

# -------------------------------
# 核心邏輯：處理玩家請求
# -------------------------------
async def handle_request(req, writer):
    collection = req.get("collection")
    action = req.get("action")
    data = req.get("data", {})

    # === 1️⃣ User 相關：註冊、登入、登出 ===
    if collection == "Dev_user":
        resp = await db_request(req)
        
        # 登入成功 → 紀錄使用者資訊
        if action in ("create", "login") and resp.get("ok"):
            uid = resp["id"]
            connected_users[writer] = uid
            print(f"👤 使用者登入：{data['name']} (id={uid})")

        # 登出 → 移除線上清單
        elif action == "logout" and resp.get("ok"):
            uid = data["id"]
            if writer in connected_users:
                del connected_users[writer]
            print(f"🗂 使用者登出：id={uid}"    )

        return resp
    
    if collection == "Dev_create_game":
        
        # === 4️⃣ Config 相關：取得 config 模板 ===
        if action == "get_template":
            # 確認模板檔案是否存在
            try:
                with open("develope/config.txt", "r", encoding="utf-8") as f:
                    template_content = f.read()
                resp = {"ok": True, "template": template_content}
            except FileNotFoundError:
                resp = {"ok": False, "error": "模板檔案 config.txt 不存在。"}
            except Exception as e:
                resp = {"ok": False, "error": f"讀取模板時發生錯誤：{str(e)}"}
            return resp
        
        elif action == "create_send":
            
            resp = await db_request({
                "collection":"Dev_game",
                "action":"create_game",
                "data":{
                    "user_id": data.get("user_id"),
                    "game_name": data.get("game_name"),
                    "config": data.get("config"),
                }
            })
            
            if resp.get("ok"):
                await create_game(resp.get("game_id"),data)
            
            return resp
            
    if collection == "Dev_update_game":
        # === 4️⃣ 更新遊戲列表 ===
        if action == "get_my_games":
            resp = await db_request(req)
            return resp
        elif action == "change_game_status":
            resp = await db_request(req)
            return resp
        elif action == "get_game_data":
            print("✅ 取得遊戲資料請求：", data)
            resp = await get_game_data(data)
            return resp
            
    
        
            
    # === 5️⃣ 其他未知請求 ===
    else:
        return {"ok": False, "error": f"未知 collection/action: {collection}/{action}"}


# -------------------------------
# 玩家連線處理
# -------------------------------
async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"📡 玩家連線: {addr}")

    try:
        while True:
            req = await recv_msg(reader)
            if not req:
                break
            #print(f"📥 收到來自 {addr}: {req}")

            resp = await handle_request(req, writer)
            await send_msg(writer, resp)

    except asyncio.IncompleteReadError:
        print(f"❌ 玩家斷線: {addr}")
    finally:
        # 清理掉線的玩家
        uid = connected_users.pop(writer, None)
        if uid is not None:
            await db_request({"collection":"Dev_user","action":"logout","data":{"id":uid}})
            print(f"🗂 使用者強制登出: id={uid}")

        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            # ✅ 忽略 WinError 64 等常見錯誤
            pass

async def create_game(game_id,data):
    
    user_id     = data.get("user_id")
    game_name   = data.get("game_name")
    config_json = data.get("config")
    server_code = data.get("server_code")
    client_code = data.get("client_code")
    
    # 建立 developer_folder
    GAMESFOLDER = Path(__file__).parent.parent / "games"
    GAMESFOLDER.mkdir(exist_ok=True)
    
    # 建立使用者專屬資料夾 [game_id]_[username]
    NEW_GAME_FOLDER = GAMESFOLDER / f"{game_id}_{game_name}"
    NEW_GAME_FOLDER.mkdir(exist_ok=True)
    
    # 寫入遊戲檔案
    config_path = NEW_GAME_FOLDER / "config.json"
    server_path = NEW_GAME_FOLDER / "game_server.py"
    client_path = NEW_GAME_FOLDER / "game_client.py"
    
    config_path.write_text(config_json, encoding="utf-8")
    server_path.write_text(server_code, encoding="utf-8")
    client_path.write_text(client_code, encoding="utf-8")
    print(f"✅ 已建立新遊戲資料夾：{NEW_GAME_FOLDER}")
    
async def get_game_data(data):
    
    game_id   = data.get("game_id")
    game_name = data.get("game_name")
    
    GAME_FOLDER = Path(__file__).parent.parent / "games" / f"{game_id}_{game_name}"
    print("✅ 讀取遊戲資料夾：", GAME_FOLDER)
    
    config_path = GAME_FOLDER / "config.json"
    server_path = GAME_FOLDER / "game_server.py"
    client_path = GAME_FOLDER / "game_client.py"
    
    data = {
        "ok": True,
        "data":{
            "game_id": game_id,
            "config": config_path.read_text(encoding="utf-8"),
            "server_code": server_path.read_text(encoding="utf-8"),
            "client_code": client_path.read_text(encoding="utf-8"),
        }
    }
    
    return data
    


# -------------------------------
# 主程式入口
# -------------------------------
async def main():
    global db_reader, db_writer

    # 啟動時就連上 DB Server
    db_reader, db_writer = await asyncio.open_connection(DB_HOST, DB_PORT)
    print(f"✅ 已連線至 DB Server {DB_HOST}:{DB_PORT}")
    
    # Lobby 初始化
    resp = await db_request({"collection": "Lobby", "action": "dev_init"})
    if resp.get("ok"):
        print("🧹 Lobby 初始化：所有使用者狀態已重設。")
    else:
        print(f"⚠️ Lobby 初始化失敗：{resp.get('error')}")

    # 啟動 Lobby Server
    server = await asyncio.start_server(handle_client, LOBBY_HOST, LOBBY_PORT)
    addr = server.sockets[0].getsockname()
    print(f"✅ Lobby Server 啟動於 {addr}")

    try:
        async with server:
            await server.serve_forever()
    finally:
        if db_writer:
            db_writer.close()
            await db_writer.wait_closed()
            print("🛑 已關閉 DB 連線。")

if __name__ == "__main__":
    asyncio.run(main())

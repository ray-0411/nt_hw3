import asyncio
import logging
from common.network import send_msg, recv_msg
import socket
import subprocess
import sys

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

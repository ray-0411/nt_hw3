import asyncio
import logging
from common.network import send_msg, recv_msg
import socket
import subprocess
import time
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
LOBBY_PORT = 14110           # Lobby Server 監聽埠
db_reader = None
db_writer = None

# -------------------------------
# 記憶體內資料結構
# -------------------------------
# online_users = {
#     user_id: {
#         "name": str,
#         "writer": asyncio.StreamWriter,  # 用來發訊息給該玩家
#         "room_id": int | None            # 目前所在房間（None 表示沒進房）
#     }
# }
online_users = {}

# rooms = {
#     room_id: {
#         "name": str,               # 房間名稱
#         "host_id": int,            # 房主使用者 ID
#         "guest_id": list[int],     # 客人 ID 清單，沒人就 []
#         "ready_status": dict[int, bool], # 玩家準備狀態
#         "all_ready": bool,         # 是否所有玩家都準備好了
#         "port": int | None,        # 遊戲伺服器埠號（還沒開就 None）
#         "game_id": int,            # 綁定哪一款遊戲（對應 dev_games.id）
#         "player_num": int,         # 目前房間實際玩家數 = 1 + len(guest_id)
#         "enabled_plugins": list[str],  # 啟用中的 plugin 名稱/ID 清單
#         "status": str               # 房間狀態：space / play / ready
#     }
# }
rooms = {}
room_counter = 0  

# invites = {
#     invitee_id: [
#         {
#             "invite_id": int,
#             "room_id": int,
#             "inviter_id": int,
#             "invitee_id": int
#         }
#     ]
# }
invites = {}
invite_counter = 0
    
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
    if collection == "User":
        resp = await db_request(req)
        
        # 登入成功 → 紀錄使用者資訊
        if action in ("create", "login") and resp.get("ok"):
            uid = resp["id"]
            online_users[uid] = {
                "name": data["name"],
                "writer": writer,
                "room_id": None
            }
            print(f"👤 使用者登入：{data['name']} (id={uid})")

        # 登出 → 移除線上清單
        elif action == "logout" and resp.get("ok"):
            uid = data["id"]
            if uid in online_users:
                online_users.pop(uid)
                print(f"👋 使用者登出 id={uid}")

        return resp


    # === 2️⃣ Room 相關 ===
    elif collection == "Room":
        
        # 建立房間（交給 DB Server 寫入）
        if action == "create":
            global room_counter
            rid = room_counter
            room_counter += 1
            
            host_id = data["host_user_id"]
            name = data.get("name", f"Room_{rid}")
            game_id = data.get("game_id", 0)
            
            rooms[rid] = {
                "name": name,
                "host_id": host_id,
                "guest_id": [],
                "game_id": game_id,
                "player_num": 1,
                "enabled_plugins": ["chat"],
                "status": "space",
                "port": None,
                "all_ready": False
            }

            # ???
            online_users[host_id]["room_id"] = rid
            # ???
            print(f"🏠 房主 {host_id} 建立房間 {rid} 遊戲{game_id}")
            return {"ok": True, "room_id": rid}

        # 列出公開房間（只轉發）
        elif action == "list":
            try:
                result = []
                
                #print(f"rooms:{rooms}")
                #print(f"online_users:{online_users}")
                
                for rid, r in rooms.items():
                    #if only_available == r["status"]:
                    if online_users[r["host_id"]]["room_id"] == rid:
                        result.append({
                            "id": rid,
                            "name": r["name"],
                            "host": online_users[r["host_id"]]["name"],
                            "status": r["status"],
                            "game_id": r["game_id"],
                        })
                    else:
                        print(f"⚠️ 房間 {rid} 狀態不符，跳過列出。")
                        print(f"host room id:{online_users[r['host_id']]['room_id']}")
                        print(f"room host id:{r['host_id']}")
                
                
                
                #***
                #print(f"result:{result}")
                
                return {"ok": True, "rooms": result}

            except Exception as e:
                #***
                #print(f"⚠️ 列出房間錯誤: {e}")
                
                return {"ok": False, "error": str(e)}
            
        elif action == "close":
            try:
                rid = data.get("room_id")
                host_id = data.get("host_user_id")

                # 🟩 檢查房間是否存在
                if rid not in rooms:
                    return {"ok": False, "error": "Room not found."}
                room = rooms[rid]

                # 🟩 確認執行者是房主
                if room["host_id"] != host_id:
                    return {"ok": False, "error": "Only the host can close the room."}
                
                # 🟩 若房間裡有 guest，通知他房間被關閉
                
                for guest_id in room.get("guest_id") or []:
                    if guest_id and guest_id in online_users:
                        online_users[guest_id]["room_id"] = None

                # 🟩 更新房主狀態
                if host_id in online_users:
                    online_users[host_id]["room_id"] = None

                # 🟩 最後刪除房間
                rooms.pop(rid)
                print(f"🗑️ 房間 {rid} 已由房主 {host_id} 關閉。")
                return {"ok": True, "msg": f"房間 {rid} 已關閉。"}
            except Exception as e:
                print(f"⚠️ 關閉房間錯誤: {e}")
                return {"ok": False, "error": str(e)}

        elif action == "join":
            rid = data.get("room_id")
            uid = data.get("user_id")

            print(f"🎯 使用者 {uid} 嘗試加入房間 {rid}")
            # 🟩 檢查房間是否存在
            if rid not in rooms:
                return {"ok": False, "error": "房間不存在。"}
            room = rooms[rid]

            return await join_room(uid, rid)
        
        elif action == "status":
            #print(f"🎯 房間狀態查詢請求：{data}")
            rid = data.get("room_id")
            room = rooms.get(rid)

            try:
                if not room:
                    return {"ok": False, "error": "Room not found."}

                # 從 online_users 查出 guest 名字
                guest_ids = room.get("guest_id") or []
                guest_names = []
                invalid_uids = []

                for uid in guest_ids:
                    if uid in online_users:
                        guest_names.append(online_users[uid]["name"])
                    else:
                        invalid_uids.append(uid)
                    
                for uid in invalid_uids:
                    rooms[rid]["guest_id"].remove(uid)
                    guest_ids.remove(uid)
                    
                
                host = get_host_ip()
                game_port = room.get("port")
                
                ready = room.get("ready_status", [])
                if ready and all(ready):
                    room["all_ready"] = True

                resp = {
                    "ok": True,
                    "status": room["status"],
                    "guest_joined": len(guest_ids) > 0,
                    "guest_id": guest_ids,
                    "guest_name": guest_names,
                    "host_id": room["host_id"],
                    "game_id": room["game_id"],
                    "game_host": host,
                    "game_port": game_port,
                    "plugins": room["enabled_plugins"],
                    "all_ready": room["all_ready"]
                }
                
                #print(f"✅ 房間 {rid} 狀態回應：{resp}")
                
                
                return resp
                
            except Exception as e:
                print(f"⚠️ 查詢房間狀態錯誤: {e}")
                print(f"🎯 房間狀態回應：{data}")
                print(f"rooms:{rooms}")
                return {"ok": False, "error": str(e)}
        
        elif action == "ready":
            rid = data.get("room_id")
            room = rooms.get(rid)

            try:
                if not room:
                    return {"ok": False, "error": "Room not found."}
                
                room["status"] = "ready"
                room["ready_status"] = [False] * len(room.get("guest_id", []))
                room["all_ready"] = False
                print(f"✅ 房主 {room['host_id']} 將房間 {rid} 設為準備狀態。")
                print(f"room:{room}")
                
                return {"ok": True, "msg": "房間已設為準備狀態。"}
                
            except Exception as e:
                print(f"⚠️ 房間準備就緒錯誤: {e}")
                return {"ok": False, "error": str(e)}

        elif action == "leave":
            rid = data.get("room_id")
            uid = data.get("user_id")

            room = rooms.get(rid)
            if not room:
                return {"ok": False, "error": "房間不存在。"}

            user_info = online_users.get(uid)
            if not user_info:
                return {"ok": False, "error": "使用者未登入。"}

            if room["guest_id"] and uid in room["guest_id"]:
                print(f"👋 玩家 {user_info['name']} 離開房間 {rid}")
                room["guest_id"] = None
                room["status"] = "space"
                user_info["room_id"] = None
                return {"ok": True, "msg": "你已離開房間。"}

            return {"ok": False, "error": "你不在該房間中。"}
            
        elif action == "guest_ready":
            rid = data.get("room_id")
            uid = data.get("user_id")

            room = rooms.get(rid)
            if not room:
                return {"ok": False, "error": "房間不存在。"}

            try:
                guest_ids = room.get("guest_id") or []
                if uid in guest_ids:
                    index = guest_ids.index(uid)
                    room["ready_status"][index] = True
                    print(f"✅ 玩家 {uid} 在房間 {rid} 標記為準備就緒。")
                    print(f"room:{room}")
                    return {"ok": True, "msg": "你已標記為準備就緒。"}
                else:
                    return {"ok": False, "error": "你不在該房間中。"}
            except Exception as e:
                print(f"⚠️ 標記玩家準備就緒錯誤: {e}")
                return {"ok": False, "error": str(e)}
        
        elif action == "start_game":
            rid = data.get("room_id")
            game_id = data.get("game_id")
            game_name = data.get("game_name")
            room = rooms.get(rid)

            try:
                if not room:
                    return {"ok": False, "error": "Room not found."}

                if room["status"] != "ready":
                    return {"ok": False, "error": "Room is not in ready status."}

                # 分配遊戲伺服器埠號
                game_port = find_free_port()
                game_host = get_host_ip()
                room["port"] = game_port
                room["status"] = "play"
                
                print(f"🚀 房間 {rid} 開始遊戲，分配埠號 {game_port}。")
                
                # 啟動遊戲伺服器子程序
                server_py = Path("games") / f"{game_id}_{game_name}" / "game_server.py"
                subprocess.Popen([sys.executable, str(server_py), str(game_port)])
                
                data = {
                    "room_id": rid,
                    "game_id": room["game_id"],
                    "host": game_host,
                    "port": game_port,
                    "player_num": room["player_num"],
                    "enabled_plugins": room["enabled_plugins"]
                }
                
                return {"ok": True, "data": data}
                
            except Exception as e:
                print(f"⚠️ 開始遊戲錯誤: {e}")
                return {"ok": False, "error": str(e)}

    # === 3️⃣ Game 相關 ===
    elif collection == "games":
        if action == "game_list":
            print("✅ 取得遊戲列表請求")
            resp = await db_request(req)
            return resp
        
        elif action == "download_game":
            
            print(f"✅ 下載遊戲資料請求：{data}")
            return await download_game(data)
        
        elif action == "get_version":
            print(f"✅ 取得遊戲版本請求：{data}")
            resp = await db_request(req)
            return resp
        
        elif action == "id_to_name":
            print(f"✅ 透過遊戲 ID 取得名稱請求：{data}")
            resp = await db_request(req)
            return resp


    # === 5️⃣ 其他未知請求 ===
    else:
        return {"ok": False, "error": f"未知 collection/action: {collection}/{action}"}

#重複function

async def join_room(uid: int, rid: int):
    try:
        room = rooms.get(rid)
        if not room:
            return {"ok": False, "error": "房間不存在。"}
        
        if uid not in online_users:
            return {"ok": False, "error": "使用者未登入。"}


        # 🟩  確認使用者沒有同時在其他房
        user_info = online_users.get(uid)
        if user_info["room_id"] is not None:
            return {"ok": False, "error": "你已在其他房間中。"}

        # 🟩 更新房間與玩家狀態
        room["guest_id"].append(uid)
        online_users[uid]["room_id"] = rid

        guest_name = user_info["name"]
        

        print(f"🎮 玩家 {guest_name} (id={uid}) 加入房間 {rid}")

        return {"ok": True, "room_id": rid}
    except Exception as e:
        print(f"⚠️ 加入房間錯誤: {e}")
        return {"ok": False, "error": str(e)}

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
        for uid, info in list(online_users.items()):
            if info["writer"] is writer:
                print(f"👋 玩家離線 id={uid}")
                
                # 通知 DB Server 登出
                try:
                    await db_request({
                        "collection": "User",
                        "action": "logout",
                        "data": {"id": uid}
                    })
                    print(f"🗂 已通知 DB Server 登出使用者 id={uid}")
                except Exception as e:
                    print(f"⚠️ 登出通知 DB Server 失敗：{e}")
                
                online_users.pop(uid)
                break
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            # ✅ 忽略 WinError 64 等常見錯誤
            pass

async def download_game(data):
    """下載指定遊戲資料"""
    game_id = data.get("game_id")
    game_name = data.get("game_name")
    
    GAME_PATH = Path(__file__).parent.parent / "games" / f"{game_id}_{game_name}"
    
    config_path = GAME_PATH / "config.json"
    game_client_path = GAME_PATH / "game_client.py"
    
    # 模擬從資料庫取得遊戲資料
    # 在真實情況下，這裡會有更多邏輯來讀取遊戲檔案
    print(f"📥 下載遊戲資料：id={game_id}, name={game_name}")
    
    try:
        if not GAME_PATH.exists():
            return {"ok": False, "error": "遊戲資料不存在。"}
        if not config_path.exists() or not game_client_path.exists():
            return {"ok": False, "error": "遊戲檔案不完整。"}
        
        # 模擬遊戲資料內容
        game_data = {
            "config": config_path.read_text(encoding="utf-8"),
            "client_code": game_client_path.read_text(encoding="utf-8"),
        }
        
        return {"ok": True, "data": game_data}
    except Exception as e:
        print(f"⚠️ 下載遊戲資料錯誤: {e}")
        return {"ok": False, "error": str(e)}
    

# -------------------------------
# 主程式入口
# -------------------------------
async def main():
    global db_reader, db_writer

    # 啟動時就連上 DB Server
    db_reader, db_writer = await asyncio.open_connection(DB_HOST, DB_PORT)
    print(f"✅ 已連線至 DB Server {DB_HOST}:{DB_PORT}")
    
    # Lobby 初始化
    resp = await db_request({"collection": "Lobby", "action": "init"})
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

import asyncio
from common.network import send_msg, recv_msg
from pathlib import Path
import json

# 🟩 你自己的候選 Lobby IP 列表
LOBBY_CANDIDATES = [
    "127.0.0.1",        # 本機測試用
    "140.113.xx.xx",    # 學校伺服器 IP（替換成真實值）
    "192.168.0.10"      # 宿舍或 VPN 環境 IP（可選）
]

LOBBY_PORT = 14110

async def connect_to_lobby():
    """嘗試依序連接多個 Lobby IP，直到成功"""
    for host in LOBBY_CANDIDATES:
        try:
            reader, writer = await asyncio.open_connection(host, LOBBY_PORT)
            print(f"✅ 已連線到 Lobby Server：{host}:{LOBBY_PORT}")
            return reader, writer
        except Exception as e:
            print(f"⚠️ 無法連線 {host}:{LOBBY_PORT} ({e})")
    raise ConnectionError("❌ 所有候選 Lobby IP 都無法連線！")


class LobbyClient:
    """封裝與 Lobby Server 的所有通訊邏輯"""

    def __init__(self, hosts=None, port=14110):
        self.hosts = hosts or [
            "140.113.66.30",   # my ip            
            "140.113.17.11",
        ]
        
        self.host = self.hosts[0]  # 預設使用第一個 host
        self.port = port
        self.reader = None
        self.writer = None
        self.user_id = None
        self.username = None
        self.lock = asyncio.Lock()

    async def connect(self):
        """嘗試多個 IP，直到成功連線到 Lobby"""
        for host in self.hosts:
            try:
                print(f"🔍 嘗試連線 Lobby：{host}:{self.port} ...")
                self.reader, self.writer = await asyncio.open_connection(host, self.port)
                self.host = host
                print(f"✅ 已連線到 Lobby Server：{host}:{self.port}")
                return True
            except Exception as e:
                print(f"⚠️ 無法連線 {host}:{self.port} ({e})")
        print("❌ 所有候選 IP 都無法連線！")
        return False


    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    # -------------------------------
    # 封裝請求/回應機制
    # -------------------------------
    async def _req(self, collection, action, data=None):
        req = {"collection": collection, "action": action, "data": data or {}}
        async with self.lock:  # ✅ 同步鎖
            await send_msg(self.writer, req)
            return await recv_msg(self.reader)

    # -------------------------------
    # 使用者相關
    # -------------------------------
    async def register(self, name, password):
        resp = await self._req("User", "create", {"name": name, "password": password})
        if resp.get("ok"):
            self.user_id = resp["id"]
            self.username = name
        return resp

    async def login(self, name, password):
        resp = await self._req("User", "login", {"name": name, "password": password})
        if resp.get("ok"):
            self.user_id = resp["id"]
            self.username = name
        return resp

    async def logout(self):
        if not self.user_id:
            return {"ok": False, "error": "尚未登入"}
        resp = await self._req("User", "logout", {"id": self.user_id})
        if resp.get("ok"):
            self.user_id = None
            self.username = None
        return resp

    async def list_online_users(self):
        return await self._req("User", "list_online")

    # -------------------------------
    # 房間相關
    # -------------------------------
    async def list_rooms(self, only_available="space"):
        data = {"only_available": only_available}
        return await self._req("Room", "list", data)

    async def create_room(self, name, game_id):
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}
        
        data = {"name": name, 
                "host_user_id": self.user_id, 
                "game_id": game_id}
        
        return await self._req("Room", "create", data)
    
    async def close_room(self, room_id):
        """關閉自己建立的房間"""
        data = {"room_id": room_id, "host_user_id": self.user_id}
        return await self._req("Room", "close", data)
    
    async def join_room(self, room_id):
        """加入指定房間"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}

        data = {
            "room_id": room_id,
            "user_id": self.user_id
        }
        
        #print(f"🚪 嘗試加入房間：{room_id} ...")
        
        return await self._req("Room", "join", data)

    async def leave_room(self, room_id):
        """離開當前房間"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}

        data = {"room_id": room_id, "user_id": self.user_id}
        return await self._req("Room", "leave", data)
    # -------------------------------
    # 邀請相關
    # -------------------------------

    async def list_games(self):
        """查詢自己建立的遊戲列表"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}

        data = {"user_id": self.user_id}
        return await self._req("games", "game_list", data)
    
    async def download_game(self, game_id, game_name):
        """下載指定遊戲資料"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}

        data = {"game_id": game_id, "game_name": game_name}
        resp = await self._req("games", "download_game", data)
        
        #print("✅ 下載遊戲回應：", resp)
        
        USER_PATH = Path(__file__).parent / f"user_{self.user_id}_{self.username}"
        USER_PATH.mkdir(exist_ok=True)
        
        GAME_PATH = USER_PATH / f"{game_id}_{game_name}"
        GAME_PATH.mkdir(exist_ok=True)
        
        config_path = GAME_PATH / "config.json"
        client_path = GAME_PATH / "game_client.py"
        
        config_path.write_text(resp.get("data").get("config"), encoding="utf-8")
        client_path.write_text(resp.get("data").get("client_code"), encoding="utf-8")
        
        print(f"✅ 已下載遊戲資料到：{GAME_PATH}")
        return resp
    
    
    async def get_game_version(self, game_id):
        """取得指定遊戲版本"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}

        data = {"game_id": game_id}
        resp = await self._req("games", "get_version", data)
        version = resp.get("current_version")
        #print(f"✅ 遊戲版本：{version}")
        return version
    
    async def get_local_game_version(self, game_id):
        """取得本地遊戲版本"""
        if not self.user_id:
            return {"ok": False, "error": "請先登入"}
        
        game_name = await self.game_id_to_name(game_id)
        #print(f"✅ 遊戲名稱：{game_name}")

        USER_PATH = Path(__file__).parent / f"user_{self.user_id}_{self.username}"
        GAME_PATH = USER_PATH / f"{game_id}_{game_name}"
        config_path = GAME_PATH / "config.json"
        
        if not config_path.exists():
            return -1

        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        local_version = config_data.get("version", "unknown")
        #print(f"✅ 本地遊戲版本：{local_version}")
        return local_version
    
    async def game_id_to_name(self, game_id):
        """將遊戲 ID 轉換為遊戲名稱"""
        #print(f"🔍 轉換遊戲 ID 為名稱：{game_id} ...")
        try:
            if not self.user_id:
                return {"ok": False, "error": "請先登入"}

            data = {"game_id": game_id}
            resp = await self._req("games", "id_to_name", data)
            if not resp.get("ok"):
                return resp
            game_name = resp.get("game_name")
            #print(f"✅ 遊戲名稱：{game_name}")
            return game_name
        except Exception as e:
            print(f"❌ 轉換遊戲 ID 為名稱失敗：{e}")
            return {"ok": False, "error": str(e)}
        
    
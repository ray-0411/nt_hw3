import asyncio
from common.network import send_msg, recv_msg


# 🟩 你自己的候選 Lobby IP 列表
LOBBY_CANDIDATES = [
    "140.113.66.30",    # my ip
    "127.0.0.1",        # 本機測試用
    "140.113.xx.xx",    # 學校伺服器 IP（替換成真實值）
    "192.168.0.10"      # 宿舍或 VPN 環境 IP（可選）
]

LOBBY_PORT = 18110  # 與 dev_lobby.py 一致

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


class DevClient:
    """封裝與 Lobby Server 的所有通訊邏輯"""

    def __init__(self, hosts=None, port=LOBBY_PORT):
        # 將本機放在首位，方便本地測試；其餘 IP 依需求調整
        self.hosts = hosts or [
            "140.113.66.30",   # my ip
            "127.0.0.1",
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
        if not self.writer:
            raise ConnectionError("尚未連線到 Lobby，請先呼叫 connect() 成功後再發送請求。")
        async with self.lock:  # ✅ 同步鎖
            await send_msg(self.writer, req)
            return await recv_msg(self.reader)

    # -------------------------------
    # 使用者相關
    # -------------------------------
    async def register(self, name, password):
        resp = await self._req("Dev_user", "create", {"name": name, "password": password})
        if resp.get("ok"):
            self.user_id = resp["id"]
            self.username = name
        return resp

    async def login(self, name, password):
        resp = await self._req("Dev_user", "login", {"name": name, "password": password})
        if resp.get("ok"):
            self.user_id = resp["id"]
            self.username = name
        return resp

    async def logout(self):
        if not self.user_id:
            return {"ok": False, "error": "尚未登入"}
        resp = await self._req("Dev_user", "logout", {"id": self.user_id})
        if resp.get("ok"):
            self.user_id = None
            self.username = None
        return resp
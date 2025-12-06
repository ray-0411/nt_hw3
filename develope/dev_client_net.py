import asyncio
from common.network import send_msg, recv_msg
import os.path
from pathlib import Path
import json


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
    
    async def get_config(self, game_folder):
        """
        獲取 config 模板並寫入指定的遊戲資料夾
        """
        resp = await self._req("Dev_create_game", "get_template")
        if resp.get("ok"):
            config_template = resp.get("template", "")
            config_path = Path(game_folder) / "config.txt"
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_template)
            print(f"✅ 已建立 config.txt：{config_path}")
        else:
            print(f"❌ 無法取得 config 模板：{resp.get('error', '未知錯誤')}")
        
        return resp
    
    async def check_config(self, game_folder):
        """
        檢查指定遊戲資料夾中的 config.txt 是否存在且非空
        """
        config_path = Path(game_folder) / "config.txt"
        
        if not config_path.exists():
            return {"ok": False, "error": "config.txt 不存在。"}
        if os.path.getsize(config_path) == 0:
            return {"ok": False, "error": "config.txt 為空檔案。"}
        
        #這裡要把config txt轉成json格式
        
        try:
            # 讀取 config.txt
            with config_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 解析 key=value 格式
            config_dict = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):  # 忽略空行和註解
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config_dict[key.strip()] = value.strip()
                else:
                    return {"ok": False, "error": f"無效的設定行：{line}"}
            
            # 轉換為 JSON
            config_json = json.dumps(config_dict, indent=4, ensure_ascii=False)
            #print("✅ config.txt 已成功轉換為 JSON 格式：")
            #print(config_json)
            
            #確認json值正確
            config_wrong = False
            if config_dict.get("name") == "*":
                config_wrong = True
            
            if version := config_dict.get("version"):
                try:
                    float(version)
                except ValueError:
                    config_wrong = True

            if config_dict.get("game_type") not in ["cli", "gui", "multi"]:
                config_wrong = True
            
            if config_dict.get("max_players"):
                try:
                    int(config_dict.get("max_players"))
                    if int(config_dict.get("max_players")) <= 0:
                        config_wrong = True
                except ValueError:
                    config_wrong = True
                
                
            
            if config_wrong:
                return {"ok": False, "error": "config.txt 內容有誤，請確認各欄位值是否正確。"}
            
            await asyncio.sleep(5)
            
            return {"ok": True, "config": config_json}
        
        
        
        except Exception as e:
            return {"ok": False, "error": f"解析 config.txt 時發生錯誤：{e}"}
        
    async def create_game(self, game_name, game_folder, config_json):
        """
        向 Lobby Server 註冊新遊戲
        """
        game_folder = Path(game_folder)
        
        server_py   = game_folder / "game_server.py"
        client_py   = game_folder / "game_client.py"
        
        
        data = {
            "user_id": self.user_id,
            "game_name": game_name,
            "config": config_json,
            "server_code": server_py.read_text(encoding="utf-8"),
            "client_code": client_py.read_text(encoding="utf-8"),
        }
        
        resp = await self._req("Dev_create_game", "create_send", data)
        return resp
    
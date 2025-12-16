import socket
import threading
import sys

class BattleshipServer:
    def __init__(self, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', int(port)))
        self.server.listen(2)
        self.clients = {}  
        self.ready_players = set()
        print(f"Server 啟動於連接埠 {port}...")

    def broadcast(self, message):
        # 統一在結尾加分割符，確保客戶端 split 後不會出錯
        msg_to_send = (message.strip('|') + "|").encode('utf-8')
        for client in self.clients.values():
            try:
                client.send(msg_to_send)
            except: pass

    def handle_client(self, client_socket, player_id):
        client_socket.send(f"ID:{player_id}|".encode('utf-8'))
        
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data: break
                
                for cmd in data.split('|'):
                    if not cmd: continue
                    print(f"收到來自玩家 {player_id} 的指令: {cmd}")
                    if cmd == "READY":
                        self.ready_players.add(player_id)
                        if len(self.ready_players) == 2:
                            self.broadcast("START")
                    else:
                        # 轉發所有攻擊 (ATTACK) 與 結果 (RESULT) 指令
                        self.broadcast(cmd)
            except: break
        
        if player_id in self.clients: del self.clients[player_id]
        client_socket.close()

    def run(self):
        while True:
            conn, addr = self.server.accept()
            if len(self.clients) < 2:
                p_id = 1 if 1 not in self.clients else 2
                self.clients[p_id] = conn
                threading.Thread(target=self.handle_client, args=(conn, p_id), daemon=True).start()

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else 5555
    BattleshipServer(port).run()
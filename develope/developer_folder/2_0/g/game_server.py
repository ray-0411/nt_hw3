import socket
import threading
import sys
import random
import time

class OldMaidServer:
    def __init__(self, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', int(port)))
        self.server.listen(5)
        self.clients = {}  # {p_id: socket}
        self.player_hands_count = {} # {p_id: count}
        self.turn_order = []
        self.current_picker_idx = 0
        print(f"多人抽鬼牌 Server 啟動於 {port}，滿 3 人即自動開始...")

    def broadcast(self, msg):
        full_msg = (msg.strip('|') + "|").encode('utf-8')
        for sock in self.clients.values():
            try: sock.send(full_msg)
            except: pass

    def start_game(self):
        print("人數已滿，正在發牌...")
        time.sleep(1) # 給予一點緩衝時間
        deck = [str(n) for n in range(1, 14)] * 4 + ["JK"]
        random.shuffle(deck)
        
        self.turn_order = sorted(list(self.clients.keys()))
        num_p = len(self.turn_order)
        
        for i, p_id in enumerate(self.turn_order):
            p_cards = deck[i::num_p]
            self.clients[p_id].send(f"CARDS:{','.join(p_cards)}|".encode('utf-8'))
        
        self.broadcast(f"INFO:遊戲開始！正在自動去對...")
        time.sleep(2) # 讓玩家看一眼原始手牌
        self.next_turn(first_time=True)

    def next_turn(self, first_time=False):
        # 尋找下一個還有牌的玩家作為 Picker
        if not first_time:
            self.current_picker_idx = (self.current_picker_idx + 1) % len(self.turn_order)
        
        # 確保 Picker 還有牌
        while self.player_hands_count.get(self.turn_order[self.current_picker_idx], 1) == 0:
            self.current_picker_idx = (self.current_picker_idx + 1) % len(self.turn_order)
            
        picker_id = self.turn_order[self.current_picker_idx]
        
        # 尋找 Picker 之後第一個還有牌的人作為 Target
        target_idx = (self.current_picker_idx + 1) % len(self.turn_order)
        while self.player_hands_count.get(self.turn_order[target_idx], 1) == 0:
            target_idx = (target_idx + 1) % len(self.turn_order)
        
        target_id = self.turn_order[target_idx]
        
        # 如果 Picker 和 Target 是同一人，代表遊戲結束
        if picker_id == target_id:
            self.broadcast(f"OVER:玩家 {picker_id} 輸了，他是最後的鬼牌得主！")
            return

        self.broadcast(f"TURN:{picker_id},{target_id}")

    def handle_client(self, conn, p_id):
        conn.send(f"ID:{p_id}|".encode('utf-8'))
        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                for cmd in data.split('|'):
                    if not cmd: continue
                    
                    if cmd.startswith("COUNT:"):
                        _, val = cmd.split(':')
                        pid, count = map(int, val.split(','))
                        self.player_hands_count[pid] = count
                        self.broadcast(cmd)
                        
                    elif cmd.startswith("DRAW_DONE:"):
                        # 抽牌動作完成，換下一位
                        time.sleep(1.5) # 抽完後停頓一下才換人
                        self.next_turn()
                        
                    else:
                        self.broadcast(cmd)
            except: break
        del self.clients[p_id]

    def run(self):
        while True:
            conn, addr = self.server.accept()
            p_id = len(self.clients) + 1
            self.clients[p_id] = conn
            print(f"玩家 {p_id} 已連線。")
            
            if len(self.clients) == 3: # 滿 3 人觸發
                threading.Thread(target=self.start_game, daemon=True).start()
            
            threading.Thread(target=self.handle_client, args=(conn, p_id), daemon=True).start()

if __name__ == "__main__":
    OldMaidServer(sys.argv[1] if len(sys.argv) > 1 else 5555).run()
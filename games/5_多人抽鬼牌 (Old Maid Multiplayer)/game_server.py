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
        self.running = True
        print(f"多人抽鬼牌 Server 啟動於 {port}，滿 3 人即自動開始...")

    def broadcast(self, msg):
        full_msg = (msg.strip('|') + "|").encode('utf-8')
        # 使用 list(self.clients.items()) 以免在迴圈中刪除字典成員報錯
        for p_id, sock in list(self.clients.items()):
            try:
                sock.send(full_msg)
            except:
                # 如果發送失敗，代表這個玩家也斷線了，直接移除
                if p_id in self.clients:
                    del self.clients[p_id]

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
        try:
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
        
        except Exception as e:
            print(f"玩家 {p_id} 通訊異常: {e}")
        finally:
            # 當程式執行到這裡，代表該玩家已經斷線
            if self.running: # 如果還沒被關閉，則執行關閉邏輯
                self.stop_game_server(p_id)
    
    def stop_game_server(self, disconnected_id):
        print(f"玩家 {disconnected_id} 斷開，正在停止伺服器...")
        self.broadcast(f"ERROR:玩家 {disconnected_id} 斷開，遊戲結束。")
        
        # 關閉所有連線
        for sock in list(self.clients.values()):
            try: sock.close()
            except: pass
        
        # 關鍵：將旗標設為 False，讓 run 迴圈停止
        self.running = False
        # 關閉監聽 socket 讓 accept 拋出例外從而跳出迴圈
        self.server.close()


    def run(self):
        print("等待玩家連線...")
        while self.running:
            try:
                conn, addr = self.server.accept()
                p_id = len(self.clients) + 1
                self.clients[p_id] = conn
                threading.Thread(target=self.handle_client, args=(conn, p_id), daemon=True).start()
                
                if len(self.clients) == 3:
                    threading.Thread(target=self.start_game, daemon=True).start()
            except:
                # 當 stop_game_server 呼叫 self.server.close() 時，
                # accept 會報錯，程式會跑到這裡並跳出迴圈
                break
        print("Server 邏輯已結束。")

if __name__ == "__main__":
    OldMaidServer(sys.argv[1] if len(sys.argv) > 1 else 5555).run()
import socket
import threading
import tkinter as tk
from tkinter import messagebox
import sys

class BattleshipClient:
    def __init__(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, int(port)))
        except:
            print("連線失敗")
            return

        self.player_id = None
        self.ships_to_place = [3, 2, 1, 1] 
        self.current_ship_idx = 0
        self.my_ships = []       
        self.forbidden_zones = set() 
        self.temp_ship = []
        self.my_hits = 0      # 我打中對方的次數
        self.enemy_hits = 0   # 對方打中我的次數
        self.is_my_turn = False
        self.phase = "WAITING_FOR_ID"

        self.root = tk.Tk()
        self.setup_gui()
        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.root.mainloop()

    def setup_gui(self):
        self.root.title("海戰棋 5x5")
        self.info_label = tk.Label(self.root, text="連線中...", font=('Arial', 10), fg="blue")
        self.info_label.pack(pady=10)

        container = tk.Frame(self.root)
        container.pack(padx=10, pady=5)

        self.my_btns = self.create_grid(tk.LabelFrame(container, text="我的棋盤 (配置中)"), self.on_my_click)
        self.my_btns[0][0].master.grid(row=0, column=0, padx=10)

        self.enemy_btns = self.create_grid(tk.LabelFrame(container, text="敵方棋盤"), self.on_enemy_click)
        self.enemy_btns[0][0].master.grid(row=0, column=1, padx=10)

    def create_grid(self, frame, callback):
        btns = []
        for r in range(5):
            row = []
            for c in range(5):
                btn = tk.Button(frame, width=4, height=2, bg="lightblue", command=lambda r=r, c=c: callback(r, c))
                btn.grid(row=r, column=c)
                row.append(btn)
            btns.append(row)
        return btns

    def on_my_click(self, r, c):
        if self.phase != "PLACEMENT": return
        if (r, c) in self.my_ships or (r, c) in self.forbidden_zones or (r, c) in self.temp_ship: return

        target_len = self.ships_to_place[self.current_ship_idx]
        if len(self.temp_ship) > 0:
            last_r, last_c = self.temp_ship[-1]
            if abs(last_r - r) + abs(last_c - c) != 1: return
            if len(self.temp_ship) == 2:
                r1, c1 = self.temp_ship[0]
                if not ((r1 == last_r == r) or (c1 == last_c == c)): return

        self.temp_ship.append((r, c))
        self.my_btns[r][c].config(bg="darkblue")

        if len(self.temp_ship) == target_len:
            self.my_ships.extend(self.temp_ship)
            for (sr, sc) in self.temp_ship:
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = sr + dr, sc + dc
                        if 0 <= nr < 5 and 0 <= nc < 5:
                            if (nr, nc) not in self.my_ships:
                                self.forbidden_zones.add((nr, nc))
                                self.my_btns[nr][nc].config(bg="#FFCCCC") 

            self.temp_ship = []
            self.current_ship_idx += 1
            if self.current_ship_idx < len(self.ships_to_place):
                self.info_label.config(text=f"請放置 {self.ships_to_place[self.current_ship_idx]} 格艦")
            else:
                self.phase = "READY_SENT"
                self.info_label.config(text="等待對手配置中...", fg="orange")
                self.socket.send("READY|".encode('utf-8'))

    def on_enemy_click(self, r, c):
        if self.phase == "BATTLE" and self.is_my_turn:
            # 只有點擊還沒打過的格子才有反應
            if self.enemy_btns[r][c]["text"] == "":
                self.is_my_turn = False # 點擊後立即鎖定，防止連點
                self.socket.send(f"ATTACK:{self.player_id},{r},{c}|".encode('utf-8'))
                self.info_label.config(text="等待攻擊結果...", fg="grey")

    def receive_messages(self):
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data: break
                for cmd in data.split('|'):
                    if cmd: self.handle_cmd(cmd)
            except: break

    def handle_cmd(self, cmd):
        if cmd.startswith("ID:"):
            self.player_id = int(cmd.split(":")[1])
            self.root.title(f"玩家 {self.player_id}")
            self.phase = "PLACEMENT"
            self.info_label.config(text=f"請放置 {self.ships_to_place[0]} 格艦")

        elif cmd == "START":
            self.phase = "BATTLE"
            self.is_my_turn = (self.player_id == 1) # 玩家 1 先手
            self.update_ui()

        elif cmd.startswith("ATTACK:"):
            # 格式: ATTACK:發動攻擊者ID,r,c
            parts = cmd.split(":")[1].split(",")
            attacker_id = int(parts[0])
            r, c = int(parts[1]), int(parts[2])

            if attacker_id != self.player_id: # 如果是我「被」攻擊
                hit = (r, c) in self.my_ships
                res = "HIT" if hit else "MISS"
                self.my_btns[r][c].config(bg="red" if hit else "white", text="X" if hit else "O")
                if hit: self.enemy_hits += 1
                
                # 回傳結果給所有人，告訴大家是「我(player_id)」被打了，結果是 res
                self.socket.send(f"RESULT:{self.player_id},{r},{c},{res}|".encode('utf-8'))
                
                if self.enemy_hits == sum(self.ships_to_place):
                    messagebox.showinfo("結束", "你輸了！所有船隻都被擊沉。")
                    self.root.destroy()
                else:
                    self.is_my_turn = True
                    self.update_ui()

        elif cmd.startswith("RESULT:"):
            # 格式: RESULT:被攻擊者ID,r,c,結果
            parts = cmd.split(":")[1].split(",")
            victim_id = int(parts[0])
            r, c, res = int(parts[1]), int(parts[2]), parts[3]

            if victim_id != self.player_id: # 如果是「對方」被打的結果回傳了
                hit = (res == "HIT")
                self.enemy_btns[r][c].config(bg="red" if hit else "white", text="X" if hit else "O")
                if hit: self.my_hits += 1
                
                if self.my_hits == sum(self.ships_to_place):
                    messagebox.showinfo("勝利", "你贏了！擊沉對方所有船隻。")
                    self.root.destroy()
                else:
                    self.is_my_turn = False
                    self.update_ui()

    def update_ui(self):
        txt = "你的回合！請攻擊" if self.is_my_turn else "對手回合，請等待..."
        color = "green" if self.is_my_turn else "red"
        self.info_label.config(text=txt, fg=color)

if __name__ == "__main__":
    h = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    p = sys.argv[2] if len(sys.argv) > 2 else 5555
    BattleshipClient(h, p)
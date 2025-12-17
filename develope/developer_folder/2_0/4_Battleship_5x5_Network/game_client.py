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
            print("連線失敗，請檢查 Server 是否已啟動")
            return

        self.player_id = None
        self.ships_to_place = [3, 2, 1, 1] 
        self.current_ship_idx = 0
        
        self.my_ships_list = []    # 存每艘船的座標 [[(r,c),(r,c)], ...]
        self.my_hits_on_me = set() # 我方被擊中的座標
        self.forbidden_zones = set() # 9格規則禁區
        self.temp_ship = []        # 當前正在放置的船隻暫存
        
        self.total_ship_cells = sum(self.ships_to_place)
        self.my_hits = 0      # 我打中對方的次數
        self.enemy_hits = 0   # 對方打中我的次數
        self.is_my_turn = False
        self.phase = "WAITING_FOR_ID"

        self.root = tk.Tk()
        self.setup_gui()
        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.root.mainloop()

    def setup_gui(self):
        self.root.title("海戰棋 5x5 - 網路整合版")
        self.info_label = tk.Label(self.root, text="連線中...", font=('Arial', 10, 'bold'), fg="blue")
        self.info_label.pack(pady=5)

        # 重製工具列
        tool_frame = tk.Frame(self.root)
        tool_frame.pack()
        self.reset_btn = tk.Button(tool_frame, text="重新佈署棋盤", command=self.manual_reset, bg="#f0f0f0")
        self.reset_btn.pack(side="left", padx=5, pady=2)

        container = tk.Frame(self.root)
        container.pack(padx=10, pady=5)

        # 棋盤初始化
        self.my_btns = self.create_grid(tk.LabelFrame(container, text="我的海域 (配置中)"), self.on_my_click)
        self.my_btns[0][0].master.grid(row=0, column=0, padx=10)

        self.enemy_btns = self.create_grid(tk.LabelFrame(container, text="敵方海域 (戰鬥區)"), self.on_enemy_click)
        self.enemy_btns[0][0].master.grid(row=0, column=1, padx=10)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        try:
            self.socket.close() # 主動切斷連線
        except:
            pass
        self.root.destroy()

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

    def manual_reset(self):
        """手動重製功能"""
        if self.phase in ["PLACEMENT", "READY_SENT"]:
            self.reset_logic()
            self.info_label.config(text=f"手動重製完成，請放置 {self.ships_to_place[0]} 格艦", fg="blue")

    def reset_logic(self):
        """清空所有佈署狀態與顏色"""
        self.my_ships_list = []
        self.my_hits_on_me = set()
        self.forbidden_zones = set()
        self.temp_ship = []
        self.current_ship_idx = 0
        self.phase = "PLACEMENT"
        
        # 關鍵修正：告訴伺服器我現在還沒準備好，請重新計算
        try:
            self.socket.send("NOT_READY|".encode('utf-8'))
        except:
            pass
        
        for r in range(5):
            for c in range(5):
                self.my_btns[r][c].config(bg="lightblue", text="")

    def on_my_click(self, r, c):
        if self.phase != "PLACEMENT": return
        
        # 取得所有已放船格
        all_placed = [cell for ship in self.my_ships_list for cell in ship]
        if (r, c) in all_placed or (r, c) in self.forbidden_zones or (r, c) in self.temp_ship:
            return

        target_len = self.ships_to_place[self.current_ship_idx]

        # --- 核心邏輯：三級艦與二級艦的直線與相鄰判定 (保留雙向放置) ---
        if len(self.temp_ship) > 0:
            # 必須與當前暫存船隻中的「任何一格」相鄰
            is_adj = any(abs(sr - r) + abs(sc - c) == 1 for sr, sc in self.temp_ship)
            if not is_adj: return 
            
            # 直線判定 (當放第三格時)
            if len(self.temp_ship) == 2:
                r0, c0 = self.temp_ship[0]
                r1, c1 = self.temp_ship[1]
                # 第三格必須與前兩格在同一 row 或同一 col
                if not ((r0 == r1 == r) or (c0 == c1 == c)):
                    return

        self.temp_ship.append((r, c))
        self.my_btns[r][c].config(bg="darkblue")

        # 船隻放置完成
        if len(self.temp_ship) == target_len:
            self.my_ships_list.append(list(self.temp_ship))
            # 計算 9 格禁區
            for (sr, sc) in self.temp_ship:
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = sr + dr, sc + dc
                        if 0 <= nr < 5 and 0 <= nc < 5:
                            curr_all = [cell for ship in self.my_ships_list for cell in ship]
                            if (nr, nc) not in curr_all:
                                self.forbidden_zones.add((nr, nc))
                                self.my_btns[nr][nc].config(bg="#FFCCCC") # 淡紅色禁區

            self.temp_ship = []
            self.current_ship_idx += 1
            
            # --- 關鍵修復：在此判斷下一艘船是否還有空間 ---
            if self.current_ship_idx < len(self.ships_to_place):
                if self.is_deadlock():
                    messagebox.showwarning("提示", "空間不足以放置剩餘船隻，棋盤將自動重製。")
                    self.reset_logic()
                else:
                    self.info_label.config(text=f"請放置 {self.ships_to_place[self.current_ship_idx]} 格艦")
            else:
                self.phase = "READY_SENT"
                self.info_label.config(text="佈署完成，等待對方就緒...", fg="orange")
                self.socket.send("READY|".encode('utf-8'))

    def is_deadlock(self):
        """檢查地圖上是否還有足夠的連續空間可以放下下一艘船"""
        # 取得下一艘船需要的長度
        target_len = self.ships_to_place[self.current_ship_idx]
        
        # 取得所有已被佔用的格子（已放船的格 + 淡紅色禁區）
        all_taken = set()
        for ship in self.my_ships_list:
            for cell in ship:
                all_taken.add(cell)
        all_taken.update(self.forbidden_zones)

        # 遍歷棋盤每一個點作為起點
        for r in range(5):
            for c in range(5):
                if (r, c) not in all_taken:
                    # 如果下一艘船只要 1 格，只要找到一個空格就沒死路
                    if target_len == 1:
                        return False
                    
                    # 檢查兩個方向：水平 (右) 與 垂直 (下)
                    for dr, dc in [(0, 1), (1, 0)]:
                        can_fit = True
                        for i in range(target_len):
                            nr, nc = r + dr*i, c + dc*i
                            # 如果超出邊界或是該格已被佔用，則此方向不行
                            if not (0 <= nr < 5 and 0 <= nc < 5 and (nr, nc) not in all_taken):
                                can_fit = False
                                break
                        
                        # 如果有一個方向放得下，就代表還沒死路
                        if can_fit:
                            return False
                            
        # 找遍全地圖都沒有任何一個方向能放下連續的 target_len 格，回傳 True (死路)
        return True

    def on_enemy_click(self, r, c):
        if self.phase == "BATTLE" and self.is_my_turn:
            if self.enemy_btns[r][c]["text"] == "":
                self.is_my_turn = False
                self.info_label.config(text="通訊中...", fg="grey")
                self.socket.send(f"ATTACK:{self.player_id},{r},{c}|".encode('utf-8'))

    def receive_messages(self):
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data: 
                    # 當 Server 主動關閉 Socket 時會執行到這
                    break 
                for cmd in data.split('|'):
                    if cmd: self.handle_cmd(cmd)
            except: 
                break
        
        # 斷線後處理：提示玩家並結束遊戲
        messagebox.showerror("連線中斷", "與伺服器的連線已斷開。")
        self.root.destroy()

    def handle_cmd(self, cmd):
        if cmd.startswith("ID:"):
            self.player_id = int(cmd.split(":")[1])
            self.root.title(f"玩家 {self.player_id}")
            self.phase = "PLACEMENT"
            self.info_label.config(text=f"請放置 {self.ships_to_place[0]} 格艦")
        elif cmd == "START":
            self.phase = "BATTLE"
            self.is_my_turn = (self.player_id == 1)
            self.update_turn_ui()
        elif cmd.startswith("ATTACK:"):
            p = cmd.split(":")[1].split(",")
            if int(p[0]) != self.player_id: self.handle_defense(int(p[1]), int(p[2]))
        elif cmd.startswith("RESULT:"):
            p = cmd.split(":")[1].split(",")
            if int(p[0]) != self.player_id: self.handle_result(int(p[1]), int(p[2]), p[3], p[4:])
        
        if cmd.startswith("OPPONENT_DISCONNECTED"):
            if self.phase != "GAME_OVER":
                self.phase = "GAME_OVER"
                messagebox.showwarning("對手斷線", "對手已離開遊戲，連線終止。")
                self.info_label.config(text="【 對手已斷開連線 】", fg="red")
                # 可選擇直接關閉或是鎖死棋盤

    def handle_defense(self, r, c):
        hit = False
        target_ship = None
        # 尋找被打中的是哪一艘船
        for ship in self.my_ships_list:
            if (r, c) in ship:
                hit = True
                target_ship = ship
                break
        
        res = "MISS"
        sunk_data = ""
        if hit:
            res = "HIT"
            self.my_hits_on_me.add((r, c))
            # 檢查整艘船是否都已擊中
            if all(cell in self.my_hits_on_me for cell in target_ship):
                res = "SUNK"
                sunk_data = ",".join([f"{cell[0]} {cell[1]}" for cell in target_ship])
                # 這裡修正：立即將整艘船（含最後一格）塗成深灰色
                for sr, sc in target_ship:
                    self.my_btns[sr][sc].config(bg="#444444", text="X")
            else:
                # 尚未全沉，只把當前格變紅
                self.my_btns[r][c].config(bg="red", text="X")
        else:
            # 沒打中
            self.my_btns[r][c].config(bg="white", text="O")
        
        # 回傳結果給所有人
        self.socket.send(f"RESULT:{self.player_id},{r},{c},{res},{sunk_data}|".encode('utf-8'))
        
        # 判斷勝負
        if len(self.my_hits_on_me) == self.total_ship_cells:
            self.phase = "GAME_OVER"
            self.info_label.config(text="【 遊戲結束：你輸了！ 】", fg="red", font=('Arial', 14, 'bold'))
        else:
            self.is_my_turn = True
            self.update_turn_ui()

    def handle_result(self, r, c, res, sunk_coords):
        if res == "MISS":
            self.enemy_btns[r][c].config(bg="white", text="O")
        else:
            self.enemy_btns[r][c].config(bg="red", text="X")
            self.my_hits += 1
            if res == "SUNK":
                for coord in sunk_coords:
                    if coord:
                        sr, sc = map(int, coord.split())
                        self.enemy_btns[sr][sc].config(bg="#444444")
                messagebox.showinfo("好球", "擊沉敵方船隻！")

        if self.my_hits == self.total_ship_cells:
            self.phase = "GAME_OVER"
            self.info_label.config(text="【 恭喜：你贏了！ 】", fg="#006400", font=('Arial', 14, 'bold'))
        else:
            self.is_my_turn = False
            self.update_turn_ui()

    def update_turn_ui(self):
        t = "你的回合！" if self.is_my_turn else "對方回合..."
        self.info_label.config(text=t, fg="green" if self.is_my_turn else "red")

if __name__ == "__main__":
    h = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    p = sys.argv[2] if len(sys.argv) > 2 else 5555
    BattleshipClient(h, p)
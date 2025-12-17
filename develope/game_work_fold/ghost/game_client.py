import socket
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import time
from collections import Counter

class OldMaidClient:
    def __init__(self, host, port, user_id):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, int(port)))
        except:
            print("無法連線至伺服器")
            return

        self.user_id = user_id
        self.p_id = None
        self.my_cards = []
        self.players_info = {} # {p_id: card_count}
        self.is_my_turn = False
        self.target_id = None
        self.is_game_over = False
        
        self.root = tk.Tk()
        self.setup_ui()
        
        threading.Thread(target=self.receive, daemon=True).start()
        self.root.mainloop()

    def setup_ui(self):
        self.root.title(f"抽鬼牌 - {self.user_id}")
        self.root.geometry("850x500") # 寬一點避免卡片擠住

        self.info = tk.Label(self.root, text="等待其他玩家加入...", font=('Arial', 12, 'bold'), fg="blue")
        self.info.pack(pady=20)
        
        # 對手區域
        self.opponents_frame = tk.Frame(self.root)
        self.opponents_frame.pack(pady=20)
        
        # 自己手牌區域
        self.my_frame = tk.LabelFrame(self.root, text="我的手牌 (My Hand)", font=('Arial', 10, 'bold'))
        self.my_frame.pack(pady=20, fill="x", padx=40)
        
        # 關鍵修正：補上這個容器，否則 update_cards_display 會報錯卡住
        self.cards_container = tk.Frame(self.my_frame)
        self.cards_container.pack(pady=10)
        self.card_labels = []

    def update_cards_display(self, highlight_idx=-1):
        """更新手牌顯示，不排序。每 10 張牌自動換行"""
        # 1. 清除 cards_container 內的所有舊橫列與標籤
        for widget in self.cards_container.winfo_children():
            widget.destroy()
        self.card_labels = []
        
        current_row_frame = None
        
        # 2. 遍歷手牌
        for i, c in enumerate(self.my_cards):
            # 每 10 張牌建立一個新的橫列 Frame (i=0, 10, 20...)
            if i % 10 == 0:
                current_row_frame = tk.Frame(self.cards_container)
                current_row_frame.pack(side="top", pady=5) # pady 增加行距
            
            # 設定顏色：JK 為淡粉紅，一般牌為白色
            bg_color = "#FFEBEE" if c == "JK" else "white"
            fg_color = "red" if c == "JK" else "black"
            
            # 如果是新抽到的牌，標註為亮橘色背景
            if i == highlight_idx:
                bg_color = "#FCE8CB" 
            
            # 建立卡片標籤並放入目前的橫列 Frame 中
            lbl = tk.Label(current_row_frame, text=c, width=6, height=4, relief="raised", 
                           bg=bg_color, fg=fg_color, font=('Arial', 11, 'bold'), bd=2)
            lbl.pack(side="left", padx=4) # padx 稍微縮小一點點，確保 10 張放得下
            self.card_labels.append(lbl)

    def visual_match_and_remove(self, is_initial=False):
        """精確配對 2 張相同牌並上色移除"""
        def process():
            if is_initial:
                for i in range(5, 0, -1):
                    self.info.config(text=f"遊戲即將開始，請觀察手牌...({i}s)", fg="blue")
                    time.sleep(1)
            else:
                self.info.config(text="抽到牌了！觀察中...", fg="orange")
                time.sleep(2)

            # --- 關鍵修正：精確找出「成對」的索引 ---
            found_pair_indices = []  # 存要上色的 Label 索引
            cards_to_remove_indices = [] # 存要移除的牌索引
            
            temp_cards = list(self.my_cards)
            already_matched = set()

            # 找出所有成對的組合（不包含鬼牌）
            for i in range(len(temp_cards)):
                if i in already_matched or temp_cards[i] == "JK":
                    continue
                for j in range(i + 1, len(temp_cards)):
                    if j in already_matched:
                        continue
                    if temp_cards[i] == temp_cards[j]:
                        # 找到一對！
                        already_matched.add(i)
                        already_matched.add(j)
                        found_pair_indices.append((i, j, temp_cards[i]))
                        break

            if found_pair_indices:
                # 定義顏色池
                color_pool = [
                    "#FCE8CB", # 杏桃粉 (Apricot)
                    "#FCF8D6", # 檸檬黃 (Lemon)
                    "#DBF6DE", # 薄荷綠 (Mint)
                    "#D9FAF7", # 天空藍 (Sky)
                    "#F6E4F9", # 薰衣草紫 (Lavender)
                    "#FCD6E3", # 櫻花粉 (Rose)
                    "#E3EFCC",  # 抹茶綠 (Tea Green)
                    "#BDF0F4" # 水晶藍 (Cyan)
                ]
                
                # 幫 Label 上色 (只針對那一對的兩個索引)
                for idx, (i, j, card_val) in enumerate(found_pair_indices):
                    color = color_pool[idx % len(color_pool)]
                    self.card_labels[i].config(bg=color)
                    self.card_labels[j].config(bg=color)
                
                self.info.config(text="發現配對！準備丟棄成對卡片...", fg="red")
                time.sleep(2) 

            # --- 執行移除：只移除已經被 match 的牌 ---
            self.my_cards = [self.my_cards[k] for k in range(len(self.my_cards)) if k not in already_matched]
            
            # 更新顯示並重設 Highlight
            self.root.after(0, lambda: self.update_cards_display(highlight_idx=-1))
            self.socket.send(f"COUNT:{self.p_id},{len(self.my_cards)}|".encode())
            
            if is_initial:
                #time.sleep(0.5)
                # 這裡主動觸發一次 UI 更新，確保文字不會停在「遊戲即將開始」
                self.root.after(0, self.final_ui_refresh)
            else:
                # 如果是抽牌回合，結束後通知 Server 換下一個人
                time.sleep(1)
                self.socket.send(f"DRAW_DONE:{self.p_id}|".encode())

        threading.Thread(target=process, daemon=True).start()
    
    def final_ui_refresh(self):
        """專門用於初始丟牌後的文字恢復"""
        if self.is_game_over: return
        # 根據目前的轉場狀態恢復文字
        if self.target_id:
            curr_picker = "自己" if self.is_my_turn else f"玩家 {self.target_id - 1 if self.target_id > 1 else 'N'}" # 簡化邏輯
            # 最保險的做法是直接根據 handle_cmd 存下的狀態重刷
            if self.is_my_turn:
                self.info.config(text=f"準備就緒！請抽 玩家 {self.target_id} 的牌", fg="green")
            else:
                self.info.config(text=f"準備就緒！等待對方抽牌...", fg="black")
        

    def draw_card(self, from_id, idx):
        """點擊對手牌堆的動作"""
        # 增加一個判斷，確保在「正在抽牌」或「等待動畫」期間不能重複點擊
        if self.is_my_turn and from_id == self.target_id:
            # 關鍵修正：立即鎖定回合狀態，防止連續點擊
            self.is_my_turn = False 
            
            # 立即更新 UI 禁用所有按鈕
            self.refresh_opponents()
            
            self.info.config(text="正在抽牌並等待回應...", fg="orange")
            self.socket.send(f"DRAW_REQ:{self.p_id},{from_id},{idx}|".encode())

    def receive(self):
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data: break
                for cmd in data.split('|'):
                    if cmd: self.handle_cmd(cmd)
            except: break

    def handle_cmd(self, cmd):
        parts = cmd.split(':')
        tag = parts[0]
        
        if tag == "ID":
            self.p_id = int(parts[1])
            self.root.title(f"玩家 {self.p_id} ({self.user_id})")
            
        elif tag == "CARDS":
            self.my_cards = parts[1].split(',')
            self.update_cards_display()
            self.visual_match_and_remove(is_initial=True)
            
        elif tag == "TURN":
            if self.is_game_over: return
            curr, target = map(int, parts[1].split(','))
            self.is_my_turn = (curr == self.p_id)
            self.target_id = target
            
            if target == self.p_id:
                import random
                random.shuffle(self.my_cards)
                # 立即刷新，讓自己看到洗牌後的新位置
                self.update_cards_display()
                # 同時也要發送一次 COUNT，確保 Server 記錄的牌數與索引同步（雖然張數沒變，但這是保險）
                self.socket.send(f"COUNT:{self.p_id},{len(self.my_cards)}|".encode('utf-8'))
            
            self.info.config(text=f"輪到 玩家 {curr} 抽 玩家 {target}", 
                             fg="green" if self.is_my_turn else "black")
            self.refresh_opponents()
            
        elif tag == "DRAW_REQ":
            p_idx, from_id, c_idx = map(int, parts[1].split(','))
            if from_id == self.p_id:
                # 關鍵修正：有人要抽我的牌前，先打亂手牌順序
                # import random
                # random.shuffle(self.my_cards)
                
                # # 更新顯示（已打亂）
                # self.update_cards_display()
                
                # 抽出一張牌 (確保索引不超出範圍)
                safe_idx = c_idx if c_idx < len(self.my_cards) else 0
                card = self.my_cards.pop(safe_idx)
                
                self.socket.send(f"DRAW_VAL:{p_idx},{card}|".encode('utf-8'))
                self.update_cards_display() # 更新顯示（已打亂且少一張）
                self.socket.send(f"COUNT:{self.p_id},{len(self.my_cards)}|".encode('utf-8'))
                
        elif tag == "DRAW_VAL":
            p_idx, card = int(parts[1].split(',')[0]), parts[1].split(',')[1]
            if p_idx == self.p_id:
                # 抽到牌加入手牌末尾
                self.my_cards.append(card)
                new_idx = len(self.my_cards) - 1
                # 關鍵修正：傳入新牌的索引位置進行標色
                self.update_cards_display(highlight_idx=new_idx)
                self.visual_match_and_remove(is_initial=False)
        
        elif tag == "COUNT":
            pid, cnt = map(int, parts[1].split(','))
            self.players_info[pid] = cnt
            self.refresh_opponents()
            
        elif tag == "INFO":
            self.info.config(text=parts[1])
            
        elif tag == "OVER":
            self.is_game_over = True
            self.info.config(text=f"【 遊戲結束 】\n{parts[1]}", fg="red", font=('Arial', 14, 'bold'))

    def refresh_opponents(self):
        """重新繪製對手的卡牌按鈕"""
        for widget in self.opponents_frame.winfo_children(): widget.destroy()
        for pid, cnt in sorted(self.players_info.items()):
            if pid == self.p_id: continue
            
            frame = tk.LabelFrame(self.opponents_frame, text=f"玩家 {pid} ({cnt}張)")
            frame.pack(side="left", padx=15)
            
            if cnt == 0:
                tk.Label(frame, text="已脫手", fg="gray").pack()
                continue

            for i in range(cnt):
                # 只有輪到我且對象正確時，按鈕才啟用
                state = "normal" if (self.is_my_turn and pid == self.target_id) else "disabled"
                tk.Button(frame, text="?", width=3, state=state,
                          command=lambda p=pid, idx=i: self.draw_card(p, idx)).pack(side="left", padx=1)

if __name__ == "__main__":
    # 啟動方式: python game_client.py {host} {port} {user_id}
    if len(sys.argv) >= 4:
        OldMaidClient(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("參數不足。用法: python game_client.py 127.0.0.1 5555 PlayerName")
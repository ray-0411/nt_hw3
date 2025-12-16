# game_server.py
import socket
import sys
import random
import threading
from collections import Counter

HOST = "0.0.0.0"
NAME = {0: "剪刀", 1: "石頭", 2: "布"}


# -------------------------
# 工具函式
# -------------------------
def send_line(conn, msg):
    conn.sendall((msg + "\n").encode())


def recv_line(conn):
    data = conn.recv(1024)
    if not data:
        raise ConnectionError("client disconnected")
    return data.decode().strip()


def judge(a, b):
    if a == b:
        return 0
    elif (a - b) % 3 == 1:
        return 1
    else:
        return -1


def most_common_type(c1, c2):
    cnt = Counter(c1 + c2)
    max_cnt = max(cnt.values())
    cand = [k for k, v in cnt.items() if v == max_cnt]
    return random.choice(cand)


# -------------------------
# Thread：收單一玩家輸入
# -------------------------
def get_choice(conn, player_idx, hands, choices):
    try:
        while True:
            send_line(conn, f"Remaining cards: {hands[player_idx]}")
            send_line(conn, "Choose a card (0/1/2):")

            try:
                c = int(recv_line(conn))
            except ValueError:
                send_line(conn, "❌ 請輸入 0 / 1 / 2")
                continue

            if c in hands[player_idx]:
                hands[player_idx].remove(c)
                choices[player_idx] = c
                return
            else:
                send_line(conn, "❌ 無效的牌，請重新輸入")

    except ConnectionError:
        choices[player_idx] = "DISCONNECT"


# -------------------------
# 主程式
# -------------------------
def main(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen(2)

    print(f"🎮 Game server listening on port {port}")

    players = []
    user_ids = []

    # === 接受兩位玩家 ===
    try:
        for i in range(2):
            conn, addr = server.accept()
            uid_line = recv_line(conn)          # USER <id>
            user_id = uid_line.split()[1]

            print(f"👤 Player connected: user_id={user_id}, addr={addr}")

            players.append(conn)
            user_ids.append(user_id)

            send_line(conn, f"You are Player {i+1} (user_id={user_id})")

    except Exception as e:
        print("❌ 玩家連線失敗:", e)
        server.close()
        return

    # === 發牌 ===
    hands = {
        0: [random.randint(0, 2) for _ in range(5)],
        1: [random.randint(0, 2) for _ in range(5)],
    }

    for i, conn in enumerate(players):
        send_line(conn, f"Your cards: {hands[i]} (0=剪刀,1=石頭,2=布)")

    common = most_common_type(hands[0], hands[1])
    for conn in players:
        send_line(conn, f"📢 開場最多的牌型是：{NAME[common]}")

    score = [0, 0]

    # === 五輪對戰（真正同步）===
    try:
        for rnd in range(5):
            for conn in players:
                send_line(conn, f"\n=== Round {rnd+1} ===")
                send_line(conn, "請出牌，輸入後等待對方")

            choices = [None, None]

            threads = []
            for i in range(2):
                t = threading.Thread(
                    target=get_choice,
                    args=(players[i], i, hands, choices)
                )
                t.start()
                threads.append(t)

            # 等待兩邊都完成
            for t in threads:
                t.join()

            # 有人斷線
            if "DISCONNECT" in choices:
                raise ConnectionError("player disconnected")

            c1, c2 = choices
            result = judge(c1, c2)

            msg = f"P1({NAME[c1]}) vs P2({NAME[c2]})"

            if result == 1:
                score[0] += 1
                msg += " → Player1 wins"
            elif result == -1:
                score[1] += 1
                msg += " → Player2 wins"
            else:
                msg += " → Draw"

            for conn in players:
                send_line(conn, msg)
                send_line(conn, f"Score: P1={score[0]} P2={score[1]}")

    except ConnectionError:
        print("⚠️ 有玩家斷線，結束遊戲")
        for conn in players:
            try:
                send_line(conn, "⚠️ 對手已斷線，遊戲結束")
            except:
                pass

    finally:
        # === 結束遊戲 ===
        try:
            if score[0] > score[1]:
                result = "🏆 Player1 wins the game"
            elif score[1] > score[0]:
                result = "🏆 Player2 wins the game"
            else:
                result = "🤝 The game is a draw"

            for conn in players:
                send_line(conn, "\n=== Game Over ===")
                send_line(conn, result)
        except:
            pass

        for conn in players:
            try:
                conn.close()
            except:
                pass

        server.close()
        print("🛑 Game server closed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python game_server.py <port>")
        sys.exit(1)

    main(int(sys.argv[1]))

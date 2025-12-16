# game/game_server.py
import socket
import threading
import sys

HOST = "0.0.0.0"

def judge(p1, p2):
    if p1 == p2:
        return "draw"
    if (p1, p2) in [("rock","scissors"), ("scissors","paper"), ("paper","rock")]:
        return "p1"
    return "p2"

def handle_game(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, port))
    server.listen(2)
    print(f"🎮 RPS Server listening on port {port}")

    players = []
    choices = []

    while len(players) < 2:
        conn, addr = server.accept()
        print(f"👤 Player connected from {addr}")
        players.append(conn)
        conn.sendall(b"Welcome to Rock-Paper-Scissors!\n")

    # 收兩位玩家的選擇
    for i, conn in enumerate(players):
        conn.sendall(b"Choose rock / paper / scissors: ")
        data = conn.recv(1024).decode().strip().lower()
        choices.append(data)

    result = judge(choices[0], choices[1])

    if result == "draw":
        msg = f"Draw! Both chose {choices[0]}\n"
        players[0].sendall(msg.encode())
        players[1].sendall(msg.encode())
    elif result == "p1":
        players[0].sendall(b"You win!\n")
        players[1].sendall(b"You lose!\n")
    else:
        players[0].sendall(b"You lose!\n")
        players[1].sendall(b"You win!\n")

    for conn in players:
        conn.close()

    server.close()
    print("🏁 Game finished.")

if __name__ == "__main__":
    port = int(sys.argv[1])
    room_id = sys.argv[2]  # 保留，符合 Lobby 呼叫格式
    handle_game(port)

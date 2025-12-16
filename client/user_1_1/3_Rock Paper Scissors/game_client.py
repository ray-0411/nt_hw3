# game/game_client.py
import socket
import sys

def main():
    host = sys.argv[1]
    port = int(sys.argv[2])
    user_id = sys.argv[3]  # 保留，符合 Lobby 格式

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    while True:
        data = s.recv(1024).decode()
        if not data:
            break
        print(data, end="")

        if "Choose" in data:
            choice = input().strip()
            s.sendall(choice.encode())

    s.close()

if __name__ == "__main__":
    main()

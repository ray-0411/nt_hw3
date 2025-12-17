# game_client.py
import socket
import sys


def main(host, port, client_user_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    # 一連線先送 user_id
    sock.sendall(f"USER {client_user_id}\n".encode())

    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("\n⚠️ 伺服器已關閉連線")
                break

            msg = data.decode()
            print(msg, end="")

            # ⭐ 只有在 server 明確要求時才輸入
            if "Choose a card" in msg:
                while True:
                    choice = input("> ").strip()
                    if choice in ("0", "1", "2"):
                        sock.sendall((choice + "\n").encode())
                        break
                    else:
                        print("❌ 請輸入 0 / 1 / 2")

    except ConnectionResetError:
        print("\n⚠️ 連線被中斷（對手或伺服器離線）")

    finally:
        sock.close()
        print("\n🔌 已離開遊戲")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python game_client.py <host> <port> <client_user_id>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    client_user_id = sys.argv[3]

    main(host, port, client_user_id)

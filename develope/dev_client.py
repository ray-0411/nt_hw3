import asyncio
from develope.dev_client_net import DevClient
import os
import time
import msvcrt
import subprocess


async def login_phase(client: DevClient):
    while True:
        #clear terminal screen
        clear_screen()
        
        print("\n=== 🧩 開發者登入選單 ===")
        print("1. 註冊")
        print("2. 登入")
        print("0. 離開")
        cmd = input("請輸入指令：").strip()

        if cmd == "1":
            name = input("使用者名稱：")
            pw = input("密碼：")
            resp = await client.register(name, pw)
            
            if resp.get("ok"):
                # ✅ 顯示註冊成功訊息
                print(f"✅ 註冊成功！歡迎，{name}！")
                time.sleep(1)
                return True
            else:
                # get error message
                error_msg = resp.get("error", "未知錯誤，請稍後再試。")

                if "already exists" in error_msg:
                    print("⚠️ 此使用者名稱已被註冊，請換一個。")
                else:
                    print(f"❌ 註冊失敗：{error_msg}")
            time.sleep(1.5)
            

        elif cmd == "2":
            name = input("使用者名稱：")
            pw = input("密碼：")
            resp = await client.login(name, pw)
            #print("📥", resp)
            
            #login successful
            if resp.get("ok"):
                print(f"✅ 登入成功！歡迎，{resp.get('name', name)}！")
                time.sleep(1)
                return True
            
            #login failed
            else:
                # get error message
                error_msg = resp.get("error", "未知錯誤，請稍後再試。")

                # 依錯誤內容做不同提示
                if error_msg == "User not found.":
                    print("❌ 帳號不存在，請先註冊。")
                elif error_msg == "Invalid password.":
                    print("❌ 密碼錯誤，請再試一次。")
                elif error_msg == "User already logged in elsewhere.":
                    print("⚠️ 該帳號已在其他地方登入。")
                else:
                    print(f"❌ 登入失敗：{error_msg}")
            time.sleep(1.5)

        elif cmd == "0":
            return False
        else:
            print("❌ 請輸入0,1,2。")

async def first_phase(client: DevClient):
    while True:
        clear_screen()
        
        print(f"\n🎮 開發者：{client.username}")
        print("1. 新建遊戲")
        print("2. 更新遊戲")
        print("3. 調整已上架遊戲")
        print("4. 登出")
        cmd = input("請輸入指令：").strip()

        if cmd == "1":
            #todo
            print("功能尚未實作，敬請期待！")
            time.sleep(1.5)
        elif cmd == "2":
            #todo
            print("功能尚未實作，敬請期待！")
            time.sleep(1.5)
        elif cmd == "3":
            #todo
            print("功能尚未實作，敬請期待！")
            time.sleep(1.5)
        elif cmd == "4":
            resp = await client.logout()
            if resp.get("ok"):
                print("✅ 已成功登出。")
                time.sleep(1)
                return
            else:
                print(f"❌ 登出失敗：{resp.get('error', '未知錯誤')}")
                time.sleep(1.5)

async def main():
    client = DevClient()
    connected = await client.connect()
    if not connected:
        print("❌ 連線失敗，請確認 Lobby Server 是否啟動以及 IP/Port 設定。")
        return
    print("✅ 已連線到 Dev Server")

    while True:
        logged_in = await login_phase(client)
        if not logged_in:
            break  # 使用者選擇離開
        await first_phase(client)
        

    await client.close()
    print("🛑 已關閉連線")

def clear_screen():
    # Windows
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

if __name__ == "__main__":
    asyncio.run(main())
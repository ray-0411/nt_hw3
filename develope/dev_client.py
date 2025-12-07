import asyncio
from develope.dev_client_net import DevClient
import os
import time
import msvcrt
import subprocess
from pathlib import Path
import json


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
    # 建立 developer_folder
    DEVELOPER_FOLDER = Path(__file__).parent / "developer_folder"
    DEVELOPER_FOLDER.mkdir(exist_ok=True)
    
    # 建立使用者專屬資料夾 [user_id]_[username]
    USER_FOLDER = DEVELOPER_FOLDER / f"{client.user_id}_{client.username}"
    USER_FOLDER.mkdir(exist_ok=True)
    
    while True:
        clear_screen()
        
        print(f"\n🎮 開發者：{client.username}")
        print("1. 新建遊戲")
        print("2. 更新遊戲")
        print("3. 調整已上架遊戲狀態")
        print("4. 登出")
        cmd = input("請輸入指令：").strip()

        if cmd == "1":
            await new_game(client, USER_FOLDER)
        elif cmd == "2":
            await update_game(client, USER_FOLDER)
            time.sleep(1.5)
        elif cmd == "3":
            await change_game_status(client)
        elif cmd == "4":
            resp = await client.logout()
            if resp.get("ok"):
                print("✅ 已成功登出。")
                time.sleep(1)
                return
            else:
                print(f"❌ 登出失敗：{resp.get('error', '未知錯誤')}")
                time.sleep(1.5)

async def new_game(client: DevClient, USER_FOLDER: Path):
    while True:
        clear_screen()
        print("\n=== 🆕 新建遊戲 ===")
        game_name = input("遊戲資料夾名稱（輸入0返回上層選單）：").strip()
        if game_name == "0":
            return
        if not game_name:
            print("❌ 遊戲資料夾名稱不可為空。")
            time.sleep(1.5)
            continue
        
        break #正確輸入遊戲名稱，跳出迴圈
    
    # 建立遊戲專屬資料夾
    GAME_FOLDER = USER_FOLDER / game_name
    GAME_FOLDER.mkdir(exist_ok=True)
    print(f"✅ 已建立遊戲資料夾：{GAME_FOLDER}")
    await asyncio.sleep(1)
    
    
    result = await client.get_config(str(GAME_FOLDER))
    if not result.get("ok"):
        print(f"❌ 無法取得 config 模板：{result.get('error', '未知錯誤')}")
        await asyncio.sleep(2)
        return
    
    
    
    while True:
        clear_screen()
        
        print("\n請在你的遊戲資料夾中放入：")
        print("1. game_server.py（遊戲伺服器程式碼）")
        print("2. game_client.py（遊戲客戶端程式碼）")
        print("並正確的修改config.txt")
        print("完成後輸入1繼續，輸入0取消新建遊戲")
        print("\n資料夾路徑：", GAME_FOLDER)
        print("\n*注意：若取消新建，該資料夾將被刪除*")
        cmd = input("請輸入指令（1繼續，0取消）：").strip()
        
        if cmd == "1":
            # todo
            # 確認 game_server.py 和 game_client.py 是否存在
            server_file = GAME_FOLDER / "game_server.py"
            client_file = GAME_FOLDER / "game_client.py"
            config_file = GAME_FOLDER / "config.txt"

            if not server_file.exists():
                print("❌ game_server.py 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            if not client_file.exists():
                print("❌ game_client.py 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            if not config_file.exists():
                print("❌ config.txt 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            # 確認 config.txt 內容是否正確（非空且非預設內容）
            request = await client.check_config(str(GAME_FOLDER))
            if not request.get("ok"):
                print(f"❌ config.txt 檢查失敗：{request.get('error', '未知錯誤')}")
                await asyncio.sleep(2)
                continue
            
            config_json = json.loads(request.get("config"))
            
            game_name = config_json.get("name", game_name)
            print(f"✅ config.txt 檢查通過，遊戲名稱：{game_name}")
            
            await client.create_game(game_name, str(GAME_FOLDER), request.get("config"))
            
            print("✅ 新建遊戲完成！請前往遊戲狀態設定處發布遊戲。")
            break
        elif cmd == "0":
            # 刪除遊戲資料夾
            try:
                for item in GAME_FOLDER.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        os.rmdir(item)
                GAME_FOLDER.rmdir()
                print("✅ 已取消新建遊戲並刪除資料夾。")
            except Exception as e:
                print(f"❌ 刪除資料夾時發生錯誤：{e}")
            break
        else:
            print("❌ 請輸入1或0。")
    
    
    
    pass


async def update_game(client: DevClient, USER_FOLDER: Path):
    
    mygames = await client.get_my_games() 
    
    if not mygames.get("ok"):
        print(f"❌ 無法取得遊戲列表：{mygames.get('error', '未知錯誤')}")
        await asyncio.sleep(2)
        return
    
    games = mygames.get("games", [])
    if not games:
        print("⚠️ 你目前沒有任何已建立的遊戲。")
        await asyncio.sleep(2)
        return
    
    while True:
        clear_screen()
        print("\n=== 🛠 更新遊戲 ===")
        for idx, game in enumerate(games, start=1):
            print(f"{idx}. {game['name']} (ID: {game['id']})")
        choice = input("請輸入要更新的遊戲編號（輸入0返回上層選單）：").strip()
        if choice == "0":
            return
        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(games):
                print("❌ 無效的遊戲編號。")
                await asyncio.sleep(2)
                continue
            selected_game = games[choice_idx]
            
            print(f"你選擇了遊戲：{selected_game['name']} (ID: {selected_game['id']})")
            break
        except ValueError:
            print("❌ 請輸入有效的數字編號。")
            await asyncio.sleep(2)
            continue
    
    GAME_FOLDER = USER_FOLDER / f"{selected_game['id']}_{selected_game['name']}"
    GAME_FOLDER.mkdir(exist_ok=True)
    
    game_id = selected_game['id']
    print("等待下載資料中...")
    config = await client.get_game_data(selected_game['id'], selected_game['name'], str(GAME_FOLDER))
    old_version = json.loads(config).get("version", "未知版本")
    print(f"✅ 下載完成，當前遊戲版本：{old_version}")
    await asyncio.sleep(1.5)
    
    while True:
        clear_screen()
        print("\n請將修改後的檔案放入以下資料夾：")
        print(f"\n遊戲資料夾路徑：{GAME_FOLDER}")
        print("修改完後輸入1上傳修改，輸入0取消更新遊戲")
        cmd = input("").strip()
        
        if cmd == "1":
            # todo
            # 確認 game_server.py 和 game_client.py 是否存在
            server_file = GAME_FOLDER / "game_server.py"
            client_file = GAME_FOLDER / "game_client.py"
            config_file = GAME_FOLDER / "config.json"

            if not server_file.exists():
                print("❌ game_server.py 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            if not client_file.exists():
                print("❌ game_client.py 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            if not config_file.exists():
                print("❌ config.json 不存在，請確認後再繼續。")
                await asyncio.sleep(2)
                continue

            # 確認 config.txt 內容是否正確（非空且非預設內容）
            request = await client.check_config_json(str(GAME_FOLDER),old_version)
            if not request.get("ok"):
                print(f"❌ config.json 檢查失敗：{request.get('error', '未知錯誤')}")
                await asyncio.sleep(2)
                continue
            
            print("✅ config.txt 檢查通過。")
            
            await client.update_game(str(GAME_FOLDER), request.get("config") ,game_id)
            
            print("✅ 更新遊戲完成！")
            break
        elif cmd == "0":
            print("✅ 已取消更新遊戲。")
            break
        else:
            print("❌ 請輸入1或0。")
            continue
    

async def change_game_status(client: DevClient):
    
    mygames = await client.get_my_games()
    if not mygames.get("ok"):
        print(f"❌ 無法取得遊戲列表：{mygames.get('error', '未知錯誤')}")
        await asyncio.sleep(2)
        return
    games = mygames.get("games", [])
    if not games:
        print("⚠️ 你目前沒有任何已建立的遊戲。")
        await asyncio.sleep(2)
        return 
    
    while True:
        clear_screen()
        print("\n=== 🎮 調整遊戲狀態 ===")
        for idx, game in enumerate(games, start=1):
            status = "上架中" if game.get("visible") else "未上架"
            print(f"{idx}. {game['name']} (ID: {game['id']}) - 狀態：{status}")
        
        print("輸入x y將遊戲編號x的狀態改為y（1=上架，0=下架）")
        print("輸入0返回上層選單")
        choice = input("").strip()
        
        if choice == "0":
            return
        try:
            parts = choice.split()
            if len(parts) != 2:
                raise ValueError
            game_idx = int(parts[0]) - 1
            new_status = int(parts[1])
            if game_idx < 0 or game_idx >= len(games) or new_status not in (0, 1):
                raise ValueError
            selected_game = games[game_idx]
            resp = await client.change_game_status(selected_game['id'], new_status)
            if resp.get("ok"):
                print(f"✅ 已將遊戲 '{selected_game['name']}' 狀態更新為 {'上架中' if new_status else '未上架'}。")
                # 更新本地遊戲列表狀態
                selected_game['visible'] = bool(new_status)
                await asyncio.sleep(2)
            else:
                print(f"❌ 更新遊戲狀態失敗：{resp.get('error', '未知錯誤')}")
                await asyncio.sleep(2)
        except ValueError:
            print("❌ 請輸入正確的格式，例如：1 1")
            await asyncio.sleep(2)

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
import asyncio
from client.client_net import LobbyClient
import os
import time
import msvcrt
import subprocess



async def login_phase(client: LobbyClient):
    while True:
        #clear terminal screen
        clear_screen()
        
        print("\n=== 🧩 登入選單 ===")
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
        

async def lobby_phase(client: LobbyClient):
    while True:
        clear_screen()
        
        print(f"\n🎮 玩家：{client.username}")
        print("1. 查看遊戲商城")
        print("2. 加入房間")
        print("3. 建立房間")
        print("4. 登出")
        cmd = input("請輸入指令：").strip()

        if cmd == "1":
            clear_screen()
            
            resp = await client.list_games()
            #print(resp)
            
            while True:
                clear_screen()
                
                if not resp.get("ok"):
                    print("⚠️ 無法取得遊戲列表。")
                    time.sleep(1.5)
                    break
                if not resp.get("games"):
                    print("（目前沒有建立的遊戲）")
                    input("\n🔙 按下 Enter 鍵返回選單...")
                    break
                
                print("\n📋 遊戲清單：")
                
                for idx , game in enumerate(resp.get("games", []), start=1):
                    print(f"{idx}.{game['name']}")
            
                cmd = input("\n輸入清單編後查看遊戲詳情，或輸入0離開：")
                if cmd == "0":
                    break
                try:
                    game = resp.get("games", [])[int(cmd)-1]
                    clear_screen()
                    print("\n🎲 遊戲詳情：")
                    print(f"遊戲名稱：{game['name']}")
                    print(f"遊戲描述：{game['short_desc']}")
                    print(f"遊戲版本：{game['current_version']}")
                    print(f"遊戲最大人數：{game['max_players']}")
                    
                    cmd2 = input("\n輸入1下載或更新遊戲，或輸入0返回：")
                    if cmd2 == "0":
                        continue
                    elif cmd2 == "1":
                        clear_screen()
                        print(f"\n⬇️ 下載遊戲：{game['name']}")
                        resp2 = await client.download_game(game['id'], game['name'])
                        
                        if resp2.get("ok"):
                            print("✅ 下載完成！")
                        else:
                            print(f"❌ 下載失敗：{resp2.get('error', '未知錯誤')}")
                        
                        input("\n🔙 按下 Enter 鍵返回遊戲清單...")
                except (ValueError, IndexError):
                    print("❌ 無效輸入，請再試一次。")
                    time.sleep(1)
                    continue
                    

        elif cmd == "2":
            finish = False
            
            while True:
                clear_screen()
                
                print("\n🏠 建立新房間(輸入0結束創房)")

                # 房間名稱
                name = input("請輸入房間名稱：").strip()
                if name == "0":
                    finish = True
                    break
                elif not name:
                    print("❌ 房間名稱不能為空！")
                    time.sleep(1)
                    continue
                else:
                    break
            
            if finish:
                continue
            
            games = await client.list_games()
            if not games.get("ok") or not games.get("games"):
                print("❌ 無法取得遊戲列表，請稍後再試。")
                time.sleep(1.5)
                continue
            
            finish = False
            while True:
                print("\n📋 選擇要玩的遊戲：")
                for idx , game in enumerate(games.get("games", []), start=1):
                    print(f"{idx}.{game['name']}")
                game_choice = input("請輸入遊戲編號（0 返回）：").strip()
                if game_choice == "0":
                    finish = True
                    break
                try:
                    game = games.get("games", [])[int(game_choice)-1]
                    selected_game_id = game['id']
                    break
                except (ValueError, IndexError):
                    print("❌ 無效輸入，請再試一次。")
                    time.sleep(1)
                    continue
            
            if finish:
                continue

            # 房間可見性
            
            clear_screen()
            print("\n🏠 建立新房間(輸入0結束創房)")
            print(f"房間名稱：{name}\n")
            print(f"📋 要玩的遊戲：{game['name']}\n")
            
            # ✅ 建立房間
            resp = await client.create_room(name, selected_game_id)

            # 顯示結果
            if resp.get("ok"):
                print(f"✅ 房間「{name}」建立成功！（遊戲：{game['name']}）")
                time.sleep(1)
                
                await room_wait_phase(client, resp["room_id"], name, selected_game_id)
            else:
                print(f"❌ 建立失敗：{resp.get('error', '未知錯誤')}")
                time.sleep(1)
                continue

            input("\n🔙 按下 Enter 鍵返回選單...")

        elif cmd == "3":
            finish = False
            while True:
                clear_screen()
                print("\n🚪 加入房間")

                # 先列出房間清單
                resp = await client.list_rooms(only_available="space")
                rooms = resp.get("rooms", [])

                if not rooms:
                    print("（目前沒有可加入的房間）")
                    input("\n🔙 按下 Enter 鍵返回選單...")
                    finish = True
                    break
                
                print("\n📋 可加入的房間清單：")
                for i, r in enumerate(rooms, start=1):
                    print(f"   {i}. {r['name']}（房主：{r['host']}，類型：{r['visibility']}）")
                
                try:
                    choice = int(input("\n請輸入要加入的房間 ID（0 返回）：").strip())
                    if choice == 0:
                        finish = True
                        break
                except ValueError:
                    print("⚠️ 請輸入有效的房間 ID。")
                    time.sleep(1)
                    continue
                
                if 1 <= choice <= len(rooms):
                    target_room = rooms[choice - 1]
                    rid = target_room["id"]
                else:
                    print("❌ 沒有這個房間。")
                    time.sleep(1)
                    continue

                # 判斷是否需要密碼
                password = None
                if target_room["visibility"] == "private":
                    password = input("請輸入房間密碼（輸入 0 返回）：").strip()
                    if password == "0":
                        finish = True
                        break
                    elif not password:
                        print("⚠️ 密碼不能為空。")
                        time.sleep(1)
                        continue

                # 如果選擇的房間沒問題就跳出迴圈
                break

            if finish:
                continue

            # ✅ 發送 join 請求
            resp = await client.join_room(rid, password)
            if resp and resp.get("ok"):
                print(f"✅ 成功加入房間：{target_room['name']} (ID={rid})")
                time.sleep(1)
                # 這裡可選擇進入房內等待畫面
                await asyncio.sleep(1) 
                await guest_wait_phase(client, rid, target_room["name"])
            else:
                print(f"❌ 加入失敗：{resp.get('error', '未知錯誤')}")
                input("\n🔙 按下 Enter 鍵返回選單...")

        elif cmd == "4":
            resp = await client.logout()
            username = resp.get('name', '玩家')
            if resp.get("ok"):
                print(f"👋 登出成功，再見 {username}！")
            else:
                print(f"⚠️ 登出失敗：{resp.get('error', '未知錯誤')}")

            time.sleep(1)
            return


        else:
            print("❌ 無效指令。")


async def room_wait_phase(client, room_id, room_name):
    """房主等待其他玩家加入的階段（非阻塞鍵盤輸入版）"""
    guest_joined = False
    guest_name = None
    stop_flag = False
    last_guest_state = None
    press_button = 0
    last_refresh = 0

    async def check_guest_join():
        #todo
        
        """背景任務：每秒檢查房間狀態"""
        nonlocal guest_joined, guest_name, stop_flag
        while not stop_flag:
            try:
                # 向伺服器查詢房間狀態
                resp = await client._req("Room", "status", {"room_id": room_id})
                if resp and resp.get("ok"):
                    guest_joined = resp.get("guest_joined", False)
                    guest_name = resp.get("guest_name", None)
                else:
                    guest_joined = False
                    guest_name = None
            except Exception as e:
                # 不中斷 loop，只印出錯誤
                print(f"⚠️ 無法檢查房間狀態：{e}")
            await asyncio.sleep(1)

    # 啟動背景檢查任務
    listener = asyncio.create_task(check_guest_join())

    try:
        while True:
            if (guest_joined != last_guest_state) or (time.time() - last_refresh > 10) \
                or press_button == 2:
                clear_screen()
                press_button = 0
                print(f"\n🏠 房間等待中：{room_name} (ID={room_id})")
                if guest_joined:
                    print(f"🎉 玩家 {guest_name} 已加入！")
                    print("【1】開始遊戲")
                    print("【2】解散房間")
                else:
                    print("（等待其他玩家加入...）")
                    print("【1】顯示線上使用者")
                    print("【2】發送邀請")
                    print("【3】離開並關閉房間")
                #print("\n💡 畫面會在狀態改變時更新")
                last_refresh = time.time()
                last_guest_state = guest_joined

            # 🔹 非阻塞鍵盤讀取
            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8", errors="ignore")

                # --- 已有 guest 的選單 ---
                if guest_joined:
                    if key == "1":  # 開始遊戲
                        clear_screen()
                        print("🚀 開始遊戲！")
                        resp = await client._req("Game", "start", {"room_id": room_id})

                        if resp.get("ok"):
                            host = resp.get("game_host")
                            port = resp.get("game_port")
                            print(f"🎮 啟動遊戲客戶端連線到 {host}:{port}")

                            #print(f"🧩 啟動參數：['python', '-m', 'game.game_server', '{port}','{client.user_id}']")
                            subprocess.run(["python", "-m", "game.client_game", host, str(port), str(client.user_id)])
                            await client.close_room(room_id)
                        else:
                            print(f"⚠️ 無法啟動遊戲：{resp.get('error')}")

                        stop_flag = True
                        break

                    elif key == "2":  # 踢出玩家
                        print(f"👢 已將 {guest_name} 踢出。")
                        await client._req("Room", "kick", {"room_id": room_id})
                        guest_joined = False
                        guest_name = None
                        await asyncio.sleep(1)

                    elif key == "3":  # 解散
                        resp = await client.close_room(room_id)
                        if resp.get("ok"):
                            print(f"👋 已關閉房間「{room_name}」")
                        else:
                            print(f"⚠️ 關閉失敗：{resp.get('error', '未知錯誤')}")
                        stop_flag = True
                        break

                # --- 沒 guest 的選單 ---
                else:
                    if key == "1":
                        clear_screen()
                        press_button = 1
                        resp = await client.list_online_users()
                        users = resp.get("users", [])
                        others = [name for uid, name in users if uid != client.user_id]
                        print("\n📋 可邀請的玩家：")
                        if not others:
                            print("（目前沒有其他玩家在線上）")
                        else:
                            for i, name in enumerate(others, start=1):
                                print(f"   {i}. {name}")
                        input("\n🔙 按下 Enter 鍵返回...")
                        press_button = 2

                    elif key == "2":
                        clear_screen()
                        press_button = 1
                        resp = await client.list_online_users()
                        users = resp.get("users", [])
                        others = [(uid, name) for uid, name in users if uid != client.user_id]
                        if not others:
                            print("⚠️ 目前沒有其他線上玩家可邀請。")
                            await asyncio.sleep(1)
                            press_button = 2
                            continue

                        print("\n📨 選擇要邀請的玩家：")
                        for i, (_, name) in enumerate(others, start=1):
                            print(f"   {i}. {name}")

                        choice = input("輸入編號（0 取消）：").strip()
                        if choice == "0":
                            press_button = 2
                            continue
                        try:
                            index = int(choice) - 1
                            target_id, target_name = others[index]
                            resp = await client.send_invite(target_id, room_id)
                            if resp.get("ok"):
                                print(f"✅ 已發送邀請給 {target_name}")
                            else:
                                print(f"❌ 邀請失敗：{resp.get('error')}")
                                input("\n🔙 按下 Enter 鍵返回...")
                        except (ValueError, IndexError):
                            print("⚠️ 無效輸入。")
                        await asyncio.sleep(1)
                        press_button = 2

                    elif key == "3":
                        resp = await client.close_room(room_id)
                        if resp.get("ok"):
                            print(f"👋 已關閉房間「{room_name}」")
                        else:
                            print(f"⚠️ 關閉失敗：{resp.get('error', '未知錯誤')}")
                        stop_flag = True
                        break

            await asyncio.sleep(0.05)  # 稍微讓出 CPU

    finally:
        stop_flag = True
        listener.cancel()


async def guest_wait_phase(client, room_id, room_name):
    """加入者等待房主開始遊戲（無需重整畫面）"""
    stop_flag = False

    async def check_room_status():
        """背景任務：定期檢查房間狀態"""
        nonlocal stop_flag
        while not stop_flag:
            try:
                resp = await client._req("Room", "status", {"room_id": room_id})
                if not resp or not resp.get("ok"):
                    print("\n❌ 房間已被解散。")
                    await asyncio.sleep(1)
                    stop_flag = True
                    break

                status = resp.get("status")
                guest_id = resp.get("guest_id")

                if not guest_id:
                    print("\n👢 你已被房主踢出房間。")
                    await asyncio.sleep(1)
                    stop_flag = True
                    break

                if status == "play":
                    clear_screen()
                    print("\n🚀 房主已開始遊戲！")
                    
                    game_host = resp.get("game_host")
                    game_port = resp.get("game_port")
                    
                    if game_host and game_port:
                        print(f"🎮 連線到遊戲伺服器 {game_host}:{game_port} ...")

                        #print(f"🧩 啟動參數：['python', '-m', 'game.game_server', '{game_port}','''{client.user_id}']")
                        subprocess.run(["python","-m","game.client_game", game_host, str(game_port),str(client.user_id)])
                        input("\n🔙 按下 Enter 鍵返回選單...")
                    else:
                        print("⚠️ 無法取得遊戲伺服器資訊 (host/port)")
                    
                    stop_flag = True
                    break

            except Exception as e:
                print(f"⚠️ 無法檢查房間狀態：{e}")
                stop_flag = True
                break

            await asyncio.sleep(1)

    # 顯示一次畫面
    clear_screen()
    print(f"\n🚪 加入房間：{room_name} (ID={room_id})")
    print("⏳ 等待房主開始遊戲...")
    print("\n【1】離開房間")
    
    listener = asyncio.create_task(check_room_status())

    try:
        while not stop_flag:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8", errors="ignore")
                if key == "1":
                    resp = await client.leave_room(room_id)
                    if resp.get("ok"):
                        print("👋 你已離開房間。")
                        stop_flag = True
                        await asyncio.sleep(1)
                    else:
                        print(f"⚠️ 離開失敗：{resp.get('error', '未知錯誤')}")
                    stop_flag = True
                    break

            await asyncio.sleep(0.05)
    finally:
        stop_flag = True
        listener.cancel()


async def main():
    client = LobbyClient()
    await client.connect()
    print("✅ 已連線到 Lobby Server")

    while True:
        logged_in = await login_phase(client)
        if not logged_in:
            break  # 使用者選擇離開
        await lobby_phase(client)

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

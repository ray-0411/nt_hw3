# 專案啟動指南

## 🖥️ 伺服器端 (Server)

**啟動順序：** 請務必先啟動 `db_server`，再啟動 `lobby_server` 或 `dev_server`。

### Windows 環境
請直接執行根目錄下預先配置好的三個 `.bat` 執行檔：
* `run_db_server.bat`
* `run_lobby_server.bat`
* `run_dev_server.bat`

### Linux 環境
請於與 `.bat` 檔案同層的資料夾下執行對應指令：

* **資料庫伺服器 (db_server):**
  ```bash
  python -m database.db_server
  ```
* **開發伺服器 (dev_server):**
  ```bash
  python -m develope.dev_lobby
  ```
* **大廳伺服器 (lobby_server):**
  ```bash
  python -m lobby.lobby_server
  ```
## 🎮 客戶端 (Client)
須先下載client資料夾和develope資料夾，接著直接執行對應的 `.bat` 檔案即可開啟遊戲：

* **大廳客戶端 (Lobby Client):** `run_client.bat`
* **開發者客戶端 (Develope Client):** `run_dev_client.bat`


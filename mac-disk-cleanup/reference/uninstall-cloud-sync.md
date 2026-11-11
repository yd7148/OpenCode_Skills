# 雲端同步軟體完整移除手冊

移除 Synology Drive Client、OneDrive 的完整檢查清單與指令。

## 通用原則

1. **先停程序，再刪檔案**，順序反過來會有孤兒行程
2. **LaunchAgents 要先 `launchctl unload`**，否則登入項目殘留
3. **CloudStorage 是使用者資料**，刪前必須驗證不會回傳雲端（見 SKILL.md 安全守則）
4. TCC 保護的容器刪不掉時，先量測大小，空殼可略過

---

## Synology Drive Client

### 1. 停止所有行程

```bash
osascript -e 'quit app "Synology Drive"' 2>/dev/null
pkill -f "SynologyDrive" 2>/dev/null
pkill -f "cloud-drive" 2>/dev/null
pkill -f "FinderSync" 2>/dev/null
sleep 3
ps aux | grep -iE "synology|cloud-drive" | grep -v grep
```

**注意**：`/Applications/Synology Drive Client.app` 內的 `cloud-drive-eventd` 是 **root 權限**行程，需 `sudo pkill` 才能清掉。

### 2. 停用登入項目

```bash
launchctl unload ~/Library/LaunchAgents/com.synology.SynologyDrive.plist
rm -f ~/Library/LaunchAgents/com.synology.SynologyDrive.plist
```

`unload` 必須在 `rm` 之前，否則 launchd 仍會記住這個 job。

### 3. 刪除使用者層檔案（不需 sudo）

```bash
rm -rf ~/Library/"Application Support"/SynologyDrive
rm -rf ~/Library/Containers/com.synology.SynologyDrive.FinderHelper
rm -rf ~/Library/Containers/com.synology.SynologyDrive.FinderHelper.FinderSync
rm -rf ~/Library/Containers/com.synology.CloudStationUI.FileProvider
rm -rf ~/Library/"Group Containers"/group.com.synology.CloudStationUI
rm -f ~/Library/Preferences/com.synology.* 2>/dev/null
```

`Application Support/SynologyDrive` 約 646 M，含客戶端本體（因為 App 實際跑在這裡）與設定。

### 4. 刪除系統層（需 sudo）

```bash
sudo rm -rf "/Applications/Synology Drive Client.app"
```

也可執行 App 內建的移除精靈（會要求管理員密碼並自動清理）：

```bash
open "/Applications/Synology Drive Client.app/Contents/SharedSupport/Remove Synology Drive Client.app"
```

### 5. CloudStorage 資料夾（使用者資料）

```bash
# 先驗證
ls -la ~/Library/CloudStorage/SynologyDrive-*
ps aux | grep -iE "synology" | grep -v grep

# 確認同步已停後才刪
rm -rf ~/Library/CloudStorage/SynologyDrive-*
```

⚠️ 刪除前務必確認 NAS 上有副本。刪除後本機與 NAS 解除連結，資料不會回傳也不會下載。

### 6. 驗證

```bash
ps aux | grep -iE "synology|cloud-drive" | grep -v grep   # 應無輸出
ls -d /Applications/*[Ss]ynology*                          # 應無輸出
ls -d ~/Library/LaunchAgents/*[Ss]ynology*                 # 應無輸出
ls ~/Library/CloudStorage/                                  # 確認殘留
```

### 常見殘留

| 路徑 | 大小 | 狀態 |
|---|---|---|
| `~/Library/Containers/com.synology.SynologyDrive.FinderHelper` | ~28 K | 空殼，TCC 保護 |
| `...FinderHelper.FinderSync` | ~28 K | 空殼，TCC 保護 |
| `...CloudStationUI.FileProvider` | ~36 K | 空殼，TCC 保護 |
| `~/Library/Group Containers/group.com.synology.CloudStationUI` | 極小 | 空殼，TCC 保護 |

合計約 100 K，**可忽略**。要清需開啟「完全檔案系統存取權限」。

---

## OneDrive

### 先確認是否真的安裝過

```bash
ls -d /Applications/OneDrive.app
mdfind "kMDItemCFBundleIdentifier == 'com.microsoft.OneDrive'"
```

**兩者都無輸出 = 從未安裝**，殘留的都是空殼，只需清理即可。

### 清理項目

```bash
rm -rf ~/OneDriveFCU
rm -rf ~/Library/Containers/com.microsoft.OneDrive-mac
rm -rf ~/Library/Containers/com.microsoft.OneDrive-mac.FileProvider
rm -rf ~/Library/Containers/com.microsoft.OneDrive-mac.FinderSync
rm -rf ~/Library/Containers/com.microsoft.OneDriveLauncher
rm -rf ~/Library/"Group Containers"/UBF8T346G9.OfficeOneDriveSyncIntegration
```

### 殘留大小參考

| 路徑 | 大小 |
|---|---|
| `com.microsoft.OneDrive-mac` | 44 K |
| `com.microsoft.OneDrive-mac.FileProvider` | 40 K |
| `com.microsoft.OneDrive-mac.FinderSync` | 32 K |
| `com.microsoft.OneDriveLauncher` | 32 K |

全部是 metadata 外殼，**合計不到 200 K，無實體資料**。

### OneDrive 的特殊性

新版 OneDrive 走 FileProvider，掛載點在 `~/Library/CloudStorage/OneDrive-<帳號名>`。

**`Resource deadlock avoided`** 是 OneDrive FileProvider 的典型症狀，代表它仍在運作。處理方式：

```bash
killall Finder          # 釋放 Finder 對目錄的鎖
# 或登出後重新登入
```

若刪除時出現此訊息且 `ps aux | grep -i onedrive` 仍有行程，先在「系統設定 → 一般 → 登入項目」停用 OneDrive，再重試。

---

## iCloud Drive

macOS 原生，**不需解除安裝**。若要釋放空間：

**系統設定 → Apple ID → iCloud → iCloud Drive → 關閉「從桌面與文件資料夾同步」**

或對特定資料夾設定「移除副本」（Finder 右鍵 → 釋放空間）。

優點：iCloud Drive 有「移除副本」功能，檔案保留在雲端、本機只留佔位符，安全且隨時可取回。**這是處理雲端資料的首選方式。**

---

## 常見問題

**Q: `rm -rf` 刪了雲端資料夾，雲端資料也被刪了？**
A: 若同步程序當下仍活著，刪除會被視為使用者刪除並同步回雲端。這就是為什麼必須先 `pkill` 再刪。

**Q: 刪完發現檔案還在？**
A: 檢查 `mount | grep -iE "onedrive|clouddocs"`，若仍掛載中，需先卸載或重新登入。

**Q: 移除清單有沒有官方來源？**
A: 有。
- Synology：Knowledge Center「How to uninstall Synology Drive Client」
- Microsoft：Microsoft Support「Uninstall OneDrive on a Mac」

**Q: 想保留設定日後重裝？**
A: 刪除前先備份 `~/Library/"Application Support"/SynologyDrive/data/config/`。
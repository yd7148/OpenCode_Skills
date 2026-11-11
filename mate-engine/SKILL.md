---
name: mate-engine
description: Mate Engine / Mate Engine X（免費輕量桌面寵物、Desktop Mate 替代品）的下載、安裝執行，以及動作數量擴充（把 Assembly-CSharp.dll 的 totalIdleAnimations / DANCE_CLIP_COUNT 提高，啟用 BlendTree 中已存在但未輪播的 idle/舞蹈動畫）。Use when asked to 下載 Mate Engine、Mate Engine 檔案、桌寵、桌面寵物、desktop pet、Desktop Mate 替代、MateEngine 下載、VRM 角色桌面寵物、mate engine download、增加 Mate 動作、增加 idle 數量、增加舞蹈數量、擴充 mate 動作、mate idle 輪播、patch MateEngine 動畫計數、mate engine anim patch。When a file download is needed, download from https://github.com/shinyflvre/Mate-Engine.
license: MIT
---

# Mate Engine

Mate Engine（伙伴引擎）是一款**免費、輕量、開源**的 Windows 桌面寵物（Desktop Pet）軟體，
是 **Desktop Mate 的免費替代品**：不綁商業角色模型、支援**自訂 VRM 角色**、可模組化（Mod）、
開源（GNU AGPL v3 + MateProv2 License），且比 Desktop Mate **更省資源**。

官方（非官方社群維護）GitHub：**https://github.com/shinyflvre/Mate-Engine**

## 下載來源（本 skill 指定的檔案來源）

本 skill 的所有檔案需求一律由此下載：

- **下載網址（唯一指定）**：`https://github.com/shinyflvre/Mate-Engine`
- 下載方式：進到該 repo 後點右側 **Releases** → 下載最新的 **公開發行版 ZIP**
  （選標示為 public release 的 ZIP，**不要**下載標示 source code 的檔案）。
- 本機實際用途：把 ZIP 解壓後執行 `MateEngineX.exe` 即可啟動桌寵。
- 若需要 Steam 板（Steam 玩家有額外內容 / 自動更新 / Workshop）：
  https://store.steampowered.com/app/3625270/MateEngine/（GitHub 版終身免費）。

## 安裝與執行

1. GitHub Releases 下載公開發行版 ZIP。
2. 解壓縮（ZIP 不需安裝，直接解壓）。
3. 執行 `MateEngineX.exe`。
4. 對桌寵點**右鍵**或按 `M` 開啟選單（FPS 設定、最前面顯示、ちび/迷你模式等）。

## 重要注意事項

- **授權**：App 採 GNU AGPL v3 + MateProv2；預設內建角色版權為 Yorshka Shop 所有，
  不允許在自建 Build 重新散佈該模型。
- **防毒誤報**：Windows Defender 偶發將 `MateEngineX.exe` 標為
  `Trojan:Script/Wacatac.B1ml`，這是**未數位簽章的誤判**；可掃 VirusTotal 驗證後執行。
- **VRM 角色**：支援自訂 `.VRM`。免費模型範例：初音ミク VRM
  （https://booth.pm/en/items/3226395）。
- **Linux**：非官方移植版 https://github.com/Marksonthegamer/Mate-Engine-Linux-Port。

## 動作數量擴充（Idle / Dance）

下載後會得到 `MateEngineX_Data\Managed\Assembly-CSharp.dll`，即可套用 patch，把
BlendTree 裡已存在但被常數寫死而沒輪播的動畫全部啟用：

- `totalIdleAnimations` 10 → **19**（啟用第 11~19 個 PET_IDLE）
- `DANCE_CLIP_COUNT` 5 → **13**（啟用第 6~13 個 PET_DANCING）

> **這是「開關」不是「加檔」**：動畫本身早就打包在 `sharedassets0.assets` 裡，
> 只是程式碼把輪播數量寫死成 10 / 5。patch 是把那個常數調大，不會新增任何動畫資源。

完整流程（dnfile+dncil 反組譯 .ctor → UnityPy 驗證 BlendTree clip 數 → Mono.Cecil
重寫 IL → dnfile 全量驗證）、**工具鏈重建方式**、常見陷阱，見：

- **`reference/anim-patch.md`**（原 `mate-engine-anim-patch` skill 全文）
- `scripts/rebuild_tools.ps1`：重建 pip/UnityPy/Mono.Cecil/PatchField.exe
  （`%TEMP%\opencode` 下的工具會被系統 Temp 清理抹掉，不能假設還在）
- `scripts/verify_ctor.py`、`scripts/verify_blendtree.py`、`scripts/sweep_dll.py`：驗證腳本
- `scripts/PatchField.cs`：PatchField.exe 的原始碼（exe 是產物，別只留 exe）
- `reference/MateEngineX-動畫節點盤點.md`：動畫節點/參數盤點記錄
- 實機套用與驗證的完整紀錄（成功輸出長什麼樣）見
  `reference/anim-patch.md` 的「已驗證實機結果」，以及 repo 根目錄的
  **`VTUBER_SETUP.md`** →「Mate Engine 桌寵設定與動作擴充」

## ⚠️ 「增加動作」有兩種，不要搞混

| | 本 skill 的 anim-patch | 外部 .unity3d 舞蹈檔 |
|---|---|---|
| 做什麼 | 調大 DLL 常數，開啟**內建**的 19 個待機 / 13 個舞蹈 | 匯入**外部** MMD 轉檔的 `.unity3d` |
| 放哪 | 改 `Assembly-CSharp.dll` | 放 `MateEngineX_Data\StreamingAssets\CustomDances\` |
| 需要 Unity | 否 | 檔案本身不需要；要自己轉檔才需要 |
| 動畫來源 | 已在 `sharedassets0.assets` | 外部下載 |

使用者說「增加動作 / 增加舞蹈 / 增加 idle 數量」時，**先判斷是哪一種**；
若對方是想要特定的 MMD 舞蹈，那要的是右欄，不是本 skill 的常數 patch。

另注意：**免費（GitHub）版沒有 Steam Workshop**（官方 <https://mateengine.de/> 版本比較表），
網路上多數教學說的「去 Workshop 下載」對免費版無效。
# 磁碟清理檢查清單

清理前後逐項打勾，確保不漏、不誤刪。

## 掃描階段

- [ ] `df -h /System/Volumes/Data` 取得基準數字
- [ ] `killall Finder`（避免 CloudStorage 掃描卡死）
- [ ] 掃描家目錄各層
- [ ] 掃描 `~/Library` 三層（Library / Application Support / Caches）
- [ ] 掃描 `/Library/Application Support`（**Adobe 常在此，別漏**）
- [ ] 掃描 `/Applications`
- [ ] 掃描 `~/Library/CloudStorage` + 同步程序狀態
- [ ] 掃描 `/private/var`（僅記錄，不操作）

## 分級階段

- [ ] A 級：快取類，標明「可重建」
- [ ] B 級：需判斷項，**每項列出內容讓使用者確認**
- [ ] C 級：使用者資料，**逐項列出子資料夾名稱**

## 刪除前驗證

- [ ] 雲端資料夾：檔案權限是否為實體檔（`ls -la`）
- [ ] 雲端資料夾：同步程序是否已停止（`ps aux`）
- [ ] 雲端資料夾：是否為佔位符（dataless）
- [ ] 確認要刪的不是 `~/Documents`、`~/Pictures` 等核心資料
- [ ] 已告知使用者「刪除不可復原」

## 執行階段

- [ ] 停止相關應用程式行程
- [ ] `launchctl unload` 登入項目（在 `rm` 之前）
- [ ] 優先 `mv` 到 `~/.Trash/`
- [ ] 路徑含空格有加引號
- [ ] 遇 `Operation not permitted` → 記錄為 TCC 保護，非權限不足
- [ ] 遇 `Resource deadlock avoided` → `killall Finder` 重試
- [ ] 需 sudo 的項目**產出指令給使用者**，不猜密碼

## 驗證階段

- [ ] `df -h /System/Volumes/Data` 重新量測
- [ ] 各目錄 `du -sh` 對照前後
- [ ] `ps aux` 確認無孤兒行程
- [ ] `ls -d` 確認 App 已移除
- [ ] 記錄仍殘留但可忽略的項目及原因

## 報告階段

- [ ] 成果總覽表（前後對比）
- [ ] Mermaid 流程圖
- [ ] 逐項明細
- [ ] 刪除資料完整清單
- [ ] 待處理事項
- [ ] 驗證指令
- [ ] 遺失風險提醒
- [ ] 檔名含日期 `YYYYMMDD`
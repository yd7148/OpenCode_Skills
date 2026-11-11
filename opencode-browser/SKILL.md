---
name: opencode-browser
description: 用 OpenCode 外掛 `@different-ai/opencode-browser`（OpenCode Browser）控制使用者「既有」的 Chrome／Edge／Chromium 視窗，沿用同一個 profile、已登入狀態與既有分頁，不另開隔離環境或重新登入。Use when asked to "啟動 BROWSER CONTROL", "控制我目前的 Chrome", "browser control", "控制瀏覽器", "操作已登入的瀏覽器", "重排 YouTube 播放清單", or any task that must run inside the user's own authenticated browser session.
license: MIT
compatibility: opencode
metadata:
  audience: opencode agents
  workflow: opencode-browser-control
  languages: zh-TW
---

# opencode-browser — 控制使用者既有的瀏覽器

OpenCode Browser 是一個 **OpenCode 外掛**，讓 agent 直接驅動使用者**已經開著、已經登入**的
Chromium 家族瀏覽器。它不是另開一個乾淨的自動化瀏覽器，而是接管使用者現有的視窗與分頁。

> 與本收藏庫既有的 [`browser-control`](../browser-control/SKILL.md) 是**不同產品**：
> `browser-control` 是獨立 CLI（Playwright + relay）；本 skill 講的是 OpenCode 外掛
> `@different-ai/opencode-browser`（native messaging + broker）。兩者可並存，工具名不衝突
> （前者 `browser-control execute`，後者 `browser_*`）。

## 為什麼要用它

| 需求 | 一般自動化瀏覽器 | OpenCode Browser |
|---|---|---|
| 沿用已登入狀態（Google／YouTube／LINE…） | 要重跑登入流程，常卡在 2FA | 直接用使用者現有 profile，零登入 |
| 使用者看得見、隨時接手 | 另開 headless 視窗 | 操作的就是使用者眼前的分頁 |
| 沿用既有分頁與工作狀態 | 全部重來 | 保留原有分頁 |
| 擴充功能登入态（Google Keep、擴充功能授權） | 無法沿用 | 沿用同一個 profile |

## 架構

```text
OpenCode agent
   │  browser_* 工具（外掛 dist/plugin.js）
   ▼
broker  ──── 具名管線 \\.\pipe\opencode-browser-<USER>
   │
   ▼
native messaging host（chrome.runtime.connectNative）
   │
   ▼
Chrome 擴充功能（OpenCode Browser Automation）
   │
   ▼
使用者的既有 profile（分頁、Cookie、已登入 session）
```

三個元件缺一不可：**外掛**（agent 端）、**native host + broker**（橋接）、**擴充功能**（瀏覽器端）。

## 安裝（一次）

```powershell
# 1. 外掛：寫入全域 opencode.json 的 plugins
opencode plugin add @different-ai/opencode-browser@latest

# 2. 安裝橋接元件（broker / native host / 登錄機碼 / 擴充功能檔案）
npx @different-ai/opencode-browser@latest install
```

安裝流程是互動式的，依序問：

| 步驟 | 內容 | 備註 |
|---|---|---|
| Step 3 | 要先在 Chrome 載入擴充功能才會繼續 | 可先用空白輸入跳過，之後用本 skill 的方式載入 |
| Step 4 | 解析擴充功能 ID | manifest 內建 `key` → ID 固定，不需手動查 |
| Step 5–6 | 裝 broker / native host / 寫登錄機碼 | `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.opencode.browser_automation` |
| Step 7 | 更新 `opencode.json` | 選「2) Global」 |
| Step 9 | 驗證 broker 與擴充功能連線 | 顯示 `hostConnected=true` 才算成功 |

> **注意**：安裝器 Step 7 寫的是 V1 欄位 `plugin`（單數）。V2 應使用 `plugins`（複數）。
> 用 `opencode plugin add` 走的才是正確欄位；不要讓安裝器改寫 `opencode.json`，
> 選「4) Skip」即可。

驗證安裝：

```powershell
npx @different-ai/opencode-browser@latest status
# 期待：Broker status: ok (hostConnected=true)
```

## 把擴充功能載入「既有 profile」

這是整套流程最關鍵、也最容易卡住的一步。

### Chrome 137+ 已移除 `--load-extension`

舊做法 `chrome.exe --load-extension=<dir>` **在 Chrome 137 以上無效**（擴充功能不會出現）。
可攜版 Chrome（本機實測 154）同樣失效。

**可行做法**：讓 Chrome 帶 `--remote-debugging-port` 啟動，再用 CDP 呼叫
`Extensions.loadUnpacked`。詳見 [`reference/extension-loading.md`](reference/extension-loading.md)。

```powershell
# 啟動既有 profile（路徑於執行時解析，不可寫死）
& $chrome --user-data-dir="<PROFILE_DIR>" --remote-debugging-port=9222
# 再用 scripts/load-extension.mjs 載入擴充功能
node scripts/load-extension.mjs 9222 "$env:USERPROFILE\.opencode-browser\extension"
```

### 擴充功能 ID 是固定的

擴充功能 `manifest.json` 內建 `key`（RSA 公鍵），因此 ID 恆為
`ncfalpcdanbcccbaakenefpokeioldgd`（v4.6.x）。計算方式：
`SHA-256(DER 公鑰)` 取前 16 bytes → 每個 nibble 映射到 `a`–`p`。
**載入前不必先查 ID**，直接載入即可由 CDP 回傳。

### 分頁保留

重啟 Chrome 會關掉原有分頁，除非開啟「繼續瀏覽上次開啟的分頁」。
做法是在 Chrome **關閉狀態**下把 profile 的 `Default/Preferences` 內
`session.restore_on_startup` 設為 `1`；**事後務必還原**（Chrome 執行中會把記憶體值
寫回檔案，用 `chrome://settings/onStartup` 或
`chrome.settingsPrivate.setPref("session.restore_on_startup", 5)` 還原）。

## Chrome 重開後怎麼恢復

擴充功能是 **CDP 暫時載入**，不會寫進 profile，Chrome 一重開就沒了。
用本 skill 附的腳本一次搞定：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-browser-control.ps1
```

腳本會：偵測 Chrome 執行檔與 profile → 帶 `--remote-debugging-port` 啟動 →
等待 CDP 就緒 → `Extensions.loadUnpacked` → 驗證 broker 連線。
路徑一律在執行時解析（`$env:USERPROFILE`、登錄檔、Get-Command），不寫死任何機器路徑。

## 驅動瀏覽器

### 工具（24 支）

| 類別 | 工具 |
|---|---|
| 分頁 | `browser_get_tabs`、`browser_open_tab`、`browser_close_tab`、`browser_claim_tab`、`browser_release_tab`、`browser_list_claims` |
| 導覽 | `browser_navigate`、`browser_back`（透過 query/scripting 達成） |
| 讀取 | `browser_query`、`browser_snapshot`、`browser_console`、`browser_errors`、`browser_status`、`browser_debug` |
| 操作 | `browser_click`、`browser_type`、`browser_select`、`browser_scroll`、`browser_highlight`、`browser_wait` |
| 其他 | `browser_screenshot`、`browser_download`、`browser_list_downloads`、`browser_set_file_input`、`browser_version` |

### CLI-first 偵錯

```powershell
npx @different-ai/opencode-browser@latest tools                      # 列出工具
npx @different-ai/opencode-browser@latest tool browser_get_tabs      # 單一工具
npx @different-ai/opencode-browser@latest tool browser_query --args '{"mode":"page_text"}'
npx @different-ai/opencode-browser@latest self-test                  # 連線煙霧測試
```

> **單一 session 原則**：每次 `npx` 啟動都是**新的外掛 session**，分頁所有權（claim）
> 是 per-session 且租約 300 秒。跨多步驟的工作若每次都開新的 `npx`，會出現
> 「分頁被別的 session 佔住」。需要多步驟時，用
> [`scripts/browser-session.mjs`](scripts/browser-session.mjs) 維持**同一個 session**。

### 真實滑鼠事件

很多控制項是 Polymer（`paper-button`、`paper-menu-button`）或 YouTube 新版
view model：**程式化的 `element.click()` 不會開啟選單**。這種情況要送真實滑鼠事件：

```js
// 先用 getBoundingClientRect 取得視口座標，再送 CDP Input 事件
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", buttons: 1, clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", buttons: 0, clickCount: 1 });
```

**座標務必用 `getBoundingClientRect()` 取得**，不要從截圖量：CDP Input 用的是
**CSS viewport 像素**，螢幕截圖還要加上瀏覽器工具列的高度偏移，兩者不一致時會點到別的元件。

### 選擇器

擴充功能內建 `deepQuerySelectorAll`，會**穿透 shadow DOM**：
`ytcp-video-row .open-menu-button` 這種跨 shadow 的選取器可直接使用。

## 實戰配方：重排 YouTube 播放清單

完整步驟與演算法見 [`reference/youtube-playlist-reorder.md`](reference/youtube-playlist-reorder.md)。
摘要：

1. **排序下拉**：公開播放清單頁頂端的 chip（顯示「手動」）→ 選項有
   手動／新增日期(最新·最舊)／最熱門／發布日期(最新·最舊)。
   「發布日期 (最舊)」可快速取得近似順序。
2. **每列動作選單**：⋮ → 「移至頂端」「移至底部」「設為播放清單縮圖」。
3. **重排演算法**：想得到目標順序，就**依目標順序的相反順序**逐筆「移至頂端」。
   每一筆搬到頂端會把其餘往後推，因此反向搬移的結果正好是目標順序。
4. **逐筆驗證**：每搬一次就重讀一次清單順序，不要相信「已點擊」。

## 踩過的坑

| 坑 | 症狀 | 解法 |
|---|---|---|
| Chrome 137+ 移除 `--load-extension` | 擴充功能沒出現、broker `hostConnected=false` | 用 CDP `Extensions.loadUnpacked` |
| 擴充功能載入後連線中斷 | `hostConnected=false` | 在 service worker 執行 `chrome.runtime.reload()`；擴充功能每 15 秒有 keepalive alarm 會重連 |
| 分頁全部消失 | 重啟 Chrome 未開啟工作階段還原 | `session.restore_on_startup=1`，事後還原 |
| `npm.ps1` 被執行原則擋下 | `npm : 無法辨識…` | 用 `npm.cmd` |
| PowerShell 5.1 把 JSON 的雙引號吃掉 | 傳給 node 的參數變成 `{selector:abc}` | JSON 參數寫進**檔案**再讀取 |
| 主控台編碼把中文輸出弄亂 | 讀到的中文是亂碼 | 結果寫成 UTF-8 檔案，用編輯工具／Node 讀取 |
| 程式化 `.click()` 開不了選單 | 選單沒出現 | 改送 CDP Input 真實滑鼠事件 |
| 用截圖座標點擊 | 點到別的影片／欄位 | 一律用 `getBoundingClientRect()` |
| 每步驟開新的 `npx` | 分頁被別的 session 佔住 | 維持單一 session（`browser-session.mjs`） |
| 在 Studio 新版找不到排序功能 | 舊版 `/playlist?list=` 編輯器已停用（錯誤頁） | 排序下拉在新版公開播放清單頁的 chip |

## 驗收

- [ ] `npx @different-ai/opencode-browser@latest status` 顯示 `hostConnected=true`
- [ ] `browser_get_tabs` 能列出使用者**既有**的分頁（而不是空白新視窗）
- [ ] 目標分頁可 `browser_claim_tab` 並讀取內容
- [ ] 每次狀態變更後都有重讀驗證，不以「已點擊」當成功

## 相關檔案

| 檔案 | 用途 |
|---|---|
| [`scripts/start-browser-control.ps1`](scripts/start-browser-control.ps1) | 啟動既有 profile 的 Chrome 並載入擴充功能 |
| [`scripts/load-extension.mjs`](scripts/load-extension.mjs) | 只做 CDP `Extensions.loadUnpacked` |
| [`scripts/browser-session.mjs`](scripts/browser-session.mjs) | 維持單一 session 的工具執行器（檔案佇列） |
| [`reference/extension-loading.md`](reference/extension-loading.md) | Chrome 137+ 限制、擴充功能 ID 計算、分頁還原細節 |
| [`reference/youtube-playlist-reorder.md`](reference/youtube-playlist-reorder.md) | YouTube 播放清單排序機制與重排演算法 |

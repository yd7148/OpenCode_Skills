# 載入擴充功能到「既有 profile」— 技術細節

## 為什麼不能直接用 `--load-extension`

Chrome 137 起，官方移除了 `--load-extension` 開關的支援（防止惡意擴充功能被靜默載入）。
本機實測可攜版 Chrome 154：帶 `--load-extension=<dir>` 啟動，
`http://127.0.0.1:<port>/json/list` **不會出現**對應的 service worker target，
擴充功能等於沒裝。

替代方案有兩條：

| 方式 | 條件 | 持久性 |
|---|---|---|
| `chrome://extensions` → 開發者模式 → 載入未封裝 | 需人工點擊（選資料夾） | **永久**（寫進 profile） |
| CDP `Extensions.loadUnpacked` | Chrome 需帶 `--remote-debugging-port` | **暫時**（Chrome 一關就沒） |

CDP 方式適合自動化與一次性排障；要在日常使用中長期存在，就用人工載入一次。

## CDP 載入步驟

### 1. 帶 debugging port 啟動 Chrome

```powershell
# 路徑一律在執行時解析
$chrome = (Get-Command chrome.exe -ErrorAction SilentlyContinue).Source
$profile = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"   # 標準安裝
# 可攜版 Chrome：<PORTABLE_DIR>\Data\profile（由執行中的 chrome.exe 命令列取得）
$cache = Join-Path $env:LOCALAPPDATA "Temp\GoogleChromePortable"

& $chrome --user-data-dir="$profile" --disk-cache-dir="$cache" --remote-debugging-port=9222
```

> **同一個 profile 不能被兩個 Chrome 實例同時使用**（profile lock）。要重啟既有 Chrome
> 必須先關掉它，否則新開的實例會退化成「開到既有視窗」，flag 直接失效。

### 2. 等待 CDP 就緒並呼叫 `Extensions.loadUnpacked`

```js
const ver = await (await fetch("http://127.0.0.1:9222/json/version")).json();
const ws = new WebSocket(ver.webSocketDebuggerUrl);   // browser 層級端點
// ... 送出：
// { id, method: "Extensions.loadUnpacked", params: { path: "<擴充功能資料夾>" } }
// 回應：{ result: { id: "<32 碼擴充功能 ID>" } }
```

瀏覽器層級端點（`/json/version` 的 `webSocketDebuggerUrl`）才有 `Extensions` 網域；
頁面層級端點（`/json/list` 裡的 `webSocketDebuggerUrl`）沒有。

### 3. 確認 service worker 活著

```js
const targets = await (await fetch("http://127.0.0.1:9222/json/list")).json();
// 應出現 service_worker  chrome-extension://<ID>/background.js
```

## 擴充功能 ID 為什麼固定

`manifest.json` 內建 `key`（base64 的 RSA SubjectPublicKeyInfo）：

```json
{
  "manifest_version": 3,
  "name": "OpenCode Browser Automation",
  "key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA…",
  "permissions": ["tabs", "nativeMessaging", "scripting", "debugger", "alarms", "storage"]
}
```

Chrome 以 **公鑰的 SHA-256 前 16 bytes** 當擴充功能 ID，每個 nibble 映射到 `a`–`p`：

```js
const crypto = require("node:crypto");
const der = Buffer.from(manifest.key, "base64");
const hash = crypto.createHash("sha256").update(der).digest();
let id = "";
for (let i = 0; i < 16; i++) {
  id += String.fromCharCode(97 + (hash[i] >> 4));
  id += String.fromCharCode(97 + (hash[i] & 0xf));
}
```

`@different-ai/opencode-browser` v4.6.x 的 ID 恆為 **`ncfalpcdanbcccbaakenefpokeioldgd`**。

> 這也表示：**native messaging host 的 `allowed_origins` 必須寫對 ID**，
> 否則擴充功能載入了也連不上 broker。安裝器會自動用 manifest 推導，
> 不要手動貼錯 ID。

## 分頁保留

Chrome 關掉再開，預設開新分頁。要在重啟後還原原有分頁：

1. **關閉 Chrome**（Preferences 會在結束時被記憶體值覆寫，所以要在關閉後才改檔案）。
2. 改 `<profile>/Default/Preferences`：

   ```json
   { "session": { "restore_on_startup": 1 } }
   ```

3. 啟動 Chrome → 會還原上次的工作階段。
4. **事後還原設定**（Chrome 執行中會把自己的值寫回檔案，直接改檔會被蓋掉）：
   - 用 UI：`chrome://settings/onStartup` 選「開啟新分頁」
   - 或用 API（在 `chrome://settings/*` 頁面的 console）：

     ```js
     await chrome.settingsPrivate.setPref("session.restore_on_startup", 5);
     ```

   > `restore_on_startup`：`1` = 繼續上次工作階段、`4` = 開啟特定網頁、`5` = 開新分頁（預設）。

另一種做法是不動設定，改用 CDP `Target.createTarget` 逐一開回原本的分頁；
但工作階段還原能保留視窗配置與分頁群組，成本最低。

## Native messaging 註冊（Windows）

Chrome 從登錄機碼讀取 native messaging host：

| 機碼路徑 | 內容 |
|---|---|
| `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.opencode.browser_automation` | manifest 檔案的絕對路徑 |
| `HKCU\Software\Chromium\NativeMessagingHosts\com.opencode.browser_automation` | 同上（Chromium） |
| `HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.opencode.browser_automation` | 同上（Brave） |
| `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.opencode.browser_automation` | 同上（Edge） |

manifest 內容：

```json
{
  "name": "com.opencode.browser_automation",
  "path": "C:\\Users\\<USER>\\.opencode-browser\\host-wrapper.cmd",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://ncfalpcdanbcccbaakenefpokeioldgd/"]
}
```

> `path` 必須指向可執行檔。包裝成 `.cmd` 時，Chrome 會透過 shell 啟動，
> 但要先確保該 cmd 內的 node 路徑存在（安裝器會寫入當時偵測到的 node 路徑）。

## 連線中斷的處理

擴充功能是 MV3，service worker 可能被回收，連線隨之中斷。症狀：
`browser_status` 回 `hostConnected: false`。

```js
// 在 service worker target 上執行
chrome.runtime.reload();
```

擴充功能本身有 keepalive alarm（每 15 秒）會自動重連，`chrome.runtime.reload()`
是立即重啟 service worker 的最快手段。恢復後 `hostConnected` 會回到 true。

## 檢查清單

```powershell
# 1. Chrome 是否帶 debugging port
Invoke-RestMethod http://127.0.0.1:9222/json/version | Select-Object Browser, webSocketDebuggerUrl

# 2. 擴充功能 target 是否存在
(Invoke-RestMethod http://127.0.0.1:9222/json/list) | Where-Object { $_.url -match "ncfalpcdanbcccbaakenefpokeioldgd" }

# 3. broker 是否連到擴充功能
npx @different-ai/opencode-browser@latest status
```

三項都通過才算 BROWSER CONTROL 可用。

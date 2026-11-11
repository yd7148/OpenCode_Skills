# opencode-auto-name 移植至 OpenCode V2 plugin 格式

日期：2026-11-11
執行環境：Windows 11（`win32`）／OpenCode v2.0.16／Node v22.23.4

---

## 1. 問題描述

前一輪（`browser-skill-setup-fix-20261111.md`）盤點時發現一項未修好的功能：

> 「移植 `opencode-auto-name` 至 V2 plugin 格式（需 `Plugin.define({id, setup})`）——
> 這是唯一還沒修好的功能。」

具體症狀：`opencode plugin list` 顯示 `opencode-auto-name` 存在，但 VERSION 與 SOURCE 皆為 `-`，
且 server log 每次啟動噴 `failed to load plugin` 警告。

---

## 2. 診斷過程與證據

### 2.1 失敗次數統計（實測）

| 項目 | 值 | 查詢方式 |
|------|----|---------|
| 首次失敗 | `2026-10-05T02:15:38Z` | log 最前筆 `failed to load plugin.*opencode-auto-name` |
| 最後一次（修正前） | `2026-11-11T01:56Z` 前 | log 尾端 |
| 累計失敗次數 | **2386** | `Select-String` 計數 |
| 成功載入次數 | **0** | log 中無成功紀錄 |
| 錯誤訊息 | `Plugin must export a default definition with an id and an effect or setup function. (cause: SchemaError(Expected object at ["default"]))` | log |

> **這不是本機設定錯誤**：上游套件自 2026-08-12 起僅有 `0.1.0 / 0.1.1 / 0.1.3` 三版，
> 最新 0.1.3 仍依賴 `@opencode-ai/plugin ^1.18.10`（V1），**沒有 V2 相容版本**。

### 2.2 V1 與 V2 的 plugin 入口差異

| | V1 | V2 |
|---|---|---|
| 匯出形式 | `export default function sessionNamePlugin(opts) { return async ({client, project, directory}) => ({ event, dispose }) }` | `export default { id, setup(ctx) }` |
| `Plugin.define` | 不存在 | `export function define(plugin) { return plugin }`（**純 identity，零檢查**） |
| 載入檢查 | — | 「default export 必須是**物件**且有 `id` 與 `setup`」→ V1 的 function 直接被拒 |

實測 `@opencode/plugin@2.2.7` 的 `dist/promise/plugin.js`：

```js
export function define(plugin) {
    return plugin;
}
```

→ 關鍵在於 **`export default` 必須是物件**。實測**純物件**（不 import `@opencode/plugin`）即可載入。

### 2.3 V2 runtime 的實測限制（寫探針 plugin 實測）

以 `~/.config/opencode/plugins/probe-v2/` 安裝探針 plugin，逐一驗證 API：

| API | 實測結果 | 影響 |
|-----|---------|------|
| `ctx.session.update({sessionID, title})` | ✅ 可用，`session.get()` 讀回新標題 | 核心功能可用 |
| `ctx.session.hook("prompt", cb)` | ✅ **觸發**，`event.prompt.text` 為使用者原始輸入 | 第一則訊息來源可用 |
| `ctx.session.hook("title", cb)` | ⚠️ 註冊成功但**不觸發** | 原生自動命名未走到 title 階段，不能依賴 |
| `ctx.event.subscribe({signal})` | ✅ 可用，收到 97 種事件型別 | 事件驅動可用 |
| `ctx.session.list()` | ❌ `TypeError: ctx.session.list is not a function` | 型別定義有、runtime 沒有 |
| `ctx.session.remove()` | ❌ `TypeError: ctx.session.remove is not a function` | 同上 |
| `ctx.session.context({sessionID})` | ✅ 可用，回傳 `SessionMessageInfo[]`，user 訊息有 `text` | 可作備援來源 |
| `ctx.id` | `undefined` | plugin 自己的 id 須由 default export 提供 |
| `ctx.options` | 未宣告時為 `{}` | 選項須內建或以物件格式宣告 |
| 純物件 export（不 import SDK） | ✅ 可載入，ID 正確顯示 | 可做到零相依 |

### 2.4 決定性發現：V2 會為每個專案各啟動一份 plugin 實例

探針 log 顯示同一個 plugin 的 `setup` 被呼叫 **4 次**，分別對應 4 個專案：

```
location = C:\Users\<USER>
location = D:\80-Opnecode\Projects\OpenCode_skill
location = D:\80-Opnecode\Projects\2026-10-GothamCity
location = D:\80-Opnecode\Projects\202608-HCL-Notes
```

且**每個實例都訂閱到全域事件**（`ctx.event.subscribe` 收到所有 session 的事件）。

**這造成第一版移植的 bug**：每個實例都為「所有 session」建立狀態並排程套用標題，
但 `prompt` hook 只有 location 相符的實例會收到 → 只有一個實例有 `firstMessage`，
其餘實例用空值算出 fallback（專案名）。多實例競爭同一 session 的標題，最後寫入者勝出。

**實測症狀**：在 `OpenCode_skill` 建立 session，標題變成 `2026-10-GothamCity`
（另一個專案的名稱）而非訊息摘要。

### 2.5 決定性發現：相對路徑在 symlink 設定檔下會重複載入

本機有兩份指向同一實體檔的 symlink：

```
~/.config/opencode/opencode.jsonc      → C:\Users\<USER>\OpenCode_skill\opencode-env\opencode.jsonc
D:\80-Opnecode\.opencode\opencode.jsonc → C:\Users\<USER>\.config\opencode\opencode.jsonc → （同上）
```

在 `plugins` 陣列宣告 `"./plugins/probe-v2"` 時，OpenCode 依**宣告該條目的設定檔所在目錄**
分別解析路徑 → 同一 plugin 被載入兩次：

```
ID                  VERSION  SOURCE
-                   local    D:\80-Opnecode\.opencode\plugins\probe-v2      ← 路徑不存在，載入失敗
probe.v2            local    C:\Users\...\config\opencode\plugins\probe-v2    ← 正常
```

且 `options` 只在其中一份生效。

---

## 3. 處理動作

### 3.1 移植策略

| 決策 | 理由 |
|------|------|
| **自建 V2 移植版**，停用 npm 套件 | 上游無 V2 版本（0.1.3 依賴 V1 SDK）；繼續等無意義 |
| **零相依**（不 import `@opencode/plugin`） | 實測純物件 export 即可載入；避免 SDK 版本綁定與安裝失敗 |
| 原始碼放 **repo 內** `opencode-session-auto-name/plugin/` | 維持「repo 為唯一真實來源」原則 |
| 用**全域自動載入**（`~/.config/opencode/plugins/`），不在 config 宣告 | 避開 symlink 重複解析；選項內建於 plugin |
| 以 `projectID` **篩選 session** | 修正多實例競爭 bug |

### 3.2 V1 → V2 對應（實作於 `plugin/index.js`）

| 能力 | V1 | V2 移植版 |
|------|----|-----------|
| plugin 入口 | `export default function(opts){ return async ({client,...}) => ({event, dispose}) }` | `export default { id: "opencode-auto-name", setup(ctx) {...} }` |
| 更新標題 | `client.session.update({path:{id},body:{title}})` | `ctx.session.update({sessionID, title})` |
| 事件來源 | `hooks.event(input)` | `ctx.event.subscribe({signal})` |
| 第一則 user 訊息 | `message.updated` + `msg.summary.title` | `ctx.session.hook("prompt")` + `event.prompt.text` |
| 清理 | 回傳物件的 `dispose()` | `setup` 回傳 cleanup 函式 |
| todo 來源 | `todo.updated` 事件 | `session.tool.called` 讀 `todowrite` 工具的 `input.todos` |

### 3.3 多實例隔離修正

```js
// 只認自己 location 的 session
const myProjectID = ctx.location?.project?.id || ""
function isMine(data) {
  if (myProjectID && data.projectID) return data.projectID === myProjectID
  ...
}
// 其他事件只處理 state 中「已追蹤」的 session
if (data.sessionID && state.has(data.sessionID)) schedule(data.sessionID)
```

### 3.4 安裝與設定變更

| 動作 | 內容 |
|------|------|
| 新增 | `opencode-session-auto-name/plugin/index.js`（8.9 KB）、`plugin/package.json` |
| 安裝 | 複製到 `~/.config/opencode/plugins/opencode-auto-name/` |
| 移除 | `npm uninstall opencode-auto-name`（V1 套件；連帶移除未使用的 `@opencode-ai/plugin@1.18.30`） |
| 設定 | `opencode.jsonc` 的 `plugins` 陣列 → `[]`（改由自動載入） |
| 文件 | `opencode-session-auto-name/SKILL.md` 更新為 V2 移植版說明 |

---

## 4. 驗證結果

| 驗證項 | 方法 | 結果 |
|--------|------|------|
| plugin 載入 | `opencode plugin list` | ✅ `opencode-auto-name` / local / 單一筆，ID 正確 |
| 無載入失敗 | log 檢查 `failed to load plugin` | ✅ 修正後 0 筆 |
| 端到端命名 | 建立 session → 送 prompt → 等 14 秒 → 讀回標題 | ✅ `New session - ...` → `請幫我分析 browser skill 比較結果並整理成 Markdown 報告` |
| 多實例隔離 | 同時在 `OpenCode_skill` 與 `2026-10-GothamCity` 各建一個 session | ✅ 兩者各由自己專案的實例命名，互不干擾 |
| 修前 bug 重現 | 第一版（未篩選） | ❌ 標題變成 `2026-10-GothamCity`（他專案名）→ 已修 |
| symlink 重複載入 | 宣告相對路徑 | ❌ 出現 2 筆 + 1 筆載入失敗 → 改用自動載入後單一筆 |
| 索引一致性 | `py scripts/gen_index.py --check` | ✅ `OK: 42 個 skill，索引與內容一致` |
| 語法 | `node --check` | ✅ 通過 |
| 零相依 | 檢查 import | ✅ 未 import `@opencode/plugin` |

---

## 5. 產出與後續

### 5.1 產出

| 檔案 | 用途 |
|------|------|
| `opencode-session-auto-name/plugin/index.js` | V2 plugin 實作（唯一真實來源） |
| `opencode-session-auto-name/plugin/package.json` | plugin 中繼資料 |
| `opencode-session-auto-name/SKILL.md` | V2 移植版文件：對照表、runtime 限制、多實例隔離、踩坑、e2e 腳本 |

### 5.2 已知限制（誠實記錄）

| 限制 | 說明 |
|------|------|
| `{task}` 變數無來源 | V2 無 `todo.updated` 事件；`todowrite` 工具在本機未啟用（agent tool 清單中不存在），需啟用 experimental todo flag 才會有值。模板用 `{firstMessage}` 時不受影響 |
| `ctx.session.hook("title")` 不觸發 | 原生自動命名流程在本機未走到 title 階段（與 issue #30662 同源）。故本移植版走 `prompt` hook + 主動 `session.update`，不依賴原生流程 |
| 每專案一份實例 | 為 OpenCode 的載入模型，非本移植版造成；已用 `projectID` 篩選隔離 |

### 5.3 後續待辦

| # | 事項 | 優先度 | 說明 |
|---|------|--------|------|
| 1 | 啟用 experimental todo flag 並驗證 `{task}` 變數 | 🟢 低 | 需 `experimental.todo`（schema flag 名 `todo`），啟用後 `todowrite` 工具才會出現在 agent tool 清單 |
| 2 | 將 plugin 部署步驟納入 `deploy.ps1` | 🟡 中 | 目前是手動複製；`deploy.ps1` 已有 `opencode-env/` 的部署邏輯，可延伸處理 `plugins/` |
| 3 | 監控上游是否釋出 V2 相容版本 | 🟢 低 | 若 `opencode-auto-name` 發出 0.2.x（V2 格式），可改用官方套件並移除自建版 |

---

## 6. 踩過的坑

| 坑 | 症狀 | 解法 |
|---|---|---|
| **多實例競爭標題** | 標題變成另一個專案的名稱 | `session.created` 以 `projectID` 篩選；其他事件只處理已追蹤的 session |
| **symlink 下相對路徑重複載入** | `opencode plugin list` 出現 2 筆、1 筆載入失敗 | 不用 config 宣告；改用 `~/.config/opencode/plugins/` 自動載入 |
| `ctx.session.list` / `remove` 型別有、runtime 沒有 | `TypeError: ... is not a function` | 實測確認後不使用；以事件驅動替代 |
| `ctx.session.hook("title")` 不觸發 | 註冊成功但無事件 | 改用 `prompt` hook + 主動 `session.update` |
| `ctx.options` 預設為 `{}` | 宣告在 config 的 options 無法傳入 | 選項內建於 `DEFAULT_CONFIG`，仍支援 `ctx.options` 覆寫 |
| 探針 plugin 殘留 | `opencode plugin list` 出現 `probe.v2` | 實測完成後立即刪除 `~/.config/opencode/plugins/probe-v2` 與 `D:\80-Opnecode\.opencode\plugins` |
| 測試用 `body2.json` / `package.json` 落到 repo | `git status` 出現未追蹤檔 | 刪除；注意 `npm init` 與暫存檔寫入的工作目錄 |

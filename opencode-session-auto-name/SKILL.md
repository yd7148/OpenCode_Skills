---
name: opencode-session-auto-name
description: 讓 opencode 的 session 標題自動以「第一次 prompt 的總結」命名（或進行中 todo）。使用本 skill 內建的 OpenCode V2 plugin（0 Token、純規則式、與模型無關、零相依），並記錄原生自動命名（small model）在 opencode/big-pickle 供應商下的已知 bug、V1→V2 plugin 移植對照與多實例隔離陷阱。Use when asked to "自動命名 session", "標題自動取名", "session 標題總結", "第一個 prompt 當作標題", "自動命名 conversation title", or to configure opencode session auto-titling.
license: MIT
compatibility: opencode
metadata:
  audience: opencode agents
  workflow: opencode-session-auto-title
  languages: zh-TW
---

# opencode-session-auto-name — Session 標題自動命名

## 路徑須知

本 skill 內的絕對路徑來自**撰寫時的機器**，在其他機器上不一定存在。執行前請：

- **skills 目錄**以 `~/.config/opencode/skills/` 為準（PowerShell 用 `Join-Path $env:USERPROFILE ".config\opencode\skills"` 推導），不要假設是 `<PROJECT_ROOT_A>\.opencode\skills\` 或任何特定磁碟機。
- **專案／輸出／暫存路徑**先確認存在；找不到就問使用者實際路徑，不要自行猜測或建立。
- 本 skill（包含 `references/`）出現的 `<USER_1>` 等前綴屬**操作紀錄範例**，不是可依賴的事實。

讓 opencode 的 session 名稱自動取自「第一次使用者 prompt 的總結」或「進行中 todo」，
解決原生開新 session 只有 `New session - ...` 泛型標題的困擾。

## 已安裝設定（本機，2026-11-11 更新）

> **2026-11-11 重大更新**：原 npm 套件 `opencode-auto-name v0.1.3` 是 **V1 格式**
> （`export default` 為 function），OpenCode V2 要求 default export 為帶 `id` 與 `setup` 的物件。
> 該套件自 **2026-10-05** 起已連續載入失敗 **2386 次**且**從未成功載入過**。
> 已改用本 repo 自建的 V2 移植版，見下方〈V2 移植版〉。

### V2 移植版（本 repo 自建）

| 項目 | 內容 |
|------|------|
| 原始碼 | `opencode-session-auto-name/plugin/index.js`（本 repo 內，唯一真實來源） |
| 安裝位置 | `<USERPROFILE>\.config\opencode\plugins\opencode-auto-name\` |
| 載入方式 | **全域自動載入**，不需在 `opencode.jsonc` 宣告 |
| 相依 | **零**（刻意不 import `@opencode/plugin`，避免版本綁定） |
| plugin ID | `opencode-auto-name` |
| 選項 | 內建於 `DEFAULT_CONFIG`：`template: "{firstMessage}"`、`maxLength: 50` |

- `template: "{firstMessage}"` → 標題**只取第一個訊息的總結**（符合「第一 prompt 總結」需求）。
  若想要「有進行中 todo 時優先顯示 todo」，改回 `"{task || firstMessage}"`。
- **不需**在 `opencode.jsonc` 的 `plugins` 陣列宣告。原因見〈踩過的坑〉第 1 條
  （symlink 重複解析會導致 plugin 被載入兩次）。

### 部署指令

```powershell
# 從本 repo 複製到全域 plugins 目錄
$repo = "D:\80-Opnecode\Projects\OpenCode_skill"
$dst  = Join-Path $env:USERPROFILE ".config\opencode\plugins\opencode-auto-name"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item "$repo\opencode-session-auto-name\plugin\index.js"     $dst -Force
Copy-Item "$repo\opencode-session-auto-name\plugin\package.json" $dst -Force
# 重新載入（設定檔變更會自動 reload；plugin 檔案變更需 touch 設定或重啟）
(Get-Item (Join-Path $env:USERPROFILE ".config\opencode\opencode.jsonc")).LastWriteTime = Get-Date
opencode plugin list   # 應只出現一筆 opencode-auto-name
```

### 驗證

```powershell
# 1) plugin 有載入且 ID 正確（不可出現重複列）
opencode plugin list

# 2) 端到端：建立 session → 送 prompt → 等 14 秒 → 標題應變成首句摘要
node <e2e script>   # 見附錄
```

### 已停用的舊設定

```jsonc
// ❌ 不要再用這個（V1 tuple + 已失效的 npm 套件）
"plugin": [["opencode-auto-name", { "template": "{firstMessage}", "maxLength": 50 }]]
"plugins": [{ "package": "opencode-auto-name", "options": {...} }]   // 套件已 npm uninstall
```

## 運作機制（opencode-auto-name）

- 監聽 `session.created` / `message.updated` / `todo.updated` / `command.executed`，
  以樣板算標題；**debounce 10s**（避免對話中標題狂跳），另每 60s 周期重查。
- 「總結」是**純規則式**，**不呼叫 LLM、0 Token、與模型無關**：
  去除開頭贅詞（"i want to"、"can you"、""請…"等）→ 取第一句 → 去尾標點 →
  超過 `maxLength` 截斷並加 `…`。
- 因此「總結」= 第一個 prompt 的**首句裁剪**，不是 AI 語意摘要。

### 樣板變數
| 變數 | 意義 |
|------|------|
| `{project}` | 專案名（git repo / 目錄 basename） |
| `{task}` | 目前 `in_progress` todo 內容 |
| `{firstMessage}` | 第一個使用者訊息的總結 |
| `{messageCount}` | 訊息數 |
| `{model}` | 目前使用的模型 |
| `{date}` / `{time}` | 日期（MM/DD）／時間（HH:MM） |

樣板語法：`{a || b}` 表示 a 為空時退回 b。

## 驗證

1. 重啟 opencode 或 touch 設定檔觸發 reload（plugin 僅啟動時載入）。
2. 新開 session → 打第一句話 → 等 ~14 秒（去抖動 10s）→ 標題列顯示該訊息首句。
3. 端到端腳本驗證（建立 session → 送 prompt → 讀回標題）見下方〈附錄：端到端驗證腳本〉。

## V1 → V2 移植對照（2026-11-11 實測）

| 能力 | V1（@opencode-ai/plugin ^1.x） | V2（@opencode/plugin ^2.x） |
|------|-------------------------------|---------------------------|
| plugin 入口 | `export default function(opts) { return async ({client, project, directory}) => ({event, dispose}) }` | `export default { id, setup(ctx) }` |
| 事件來源 | V1 的 `hooks.event` | `ctx.event.subscribe({ signal })`（AsyncIterable；cleanup 時 `abort()`） |
| 更新標題 | `client.session.update({ path: { id }, body: { title } })` | `ctx.session.update({ sessionID, title })` ✅ 實測可用 |
| 第一則 user 訊息 | `message.updated` 事件的 `msg.role === 'user'` + `msg.summary.title` | `ctx.session.hook("prompt")` 的 `event.prompt.text` ✅ 實測可用 |
| 清理 | 回傳物件的 `dispose()` | `setup` 回傳 cleanup 函式 |

### V2 runtime 的實測限制（2026-11-11，OpenCode v2.0.16）

| 限制 | 影響 | 本移植版的處理 |
|------|------|--------------|
| `ctx.session.list` 型別定義存在但 **runtime 不存在** | 不能列舉所有 session | 不使用；改由事件驅動 |
| `ctx.session.remove` 同上 | 不能刪 session | 不使用 |
| `ctx.id` 為 `undefined` | plugin 自己的 id 需自行提供 | 由 `export default { id: "opencode-auto-name" }` 提供 |
| `ctx.options` 在未以物件格式宣告時為 `{}` | 無法從 config 傳 options | 選項內建於 `DEFAULT_CONFIG`；仍支援 `ctx.options` 覆寫 |
| 沒有 `todo.updated` 事件 | `{task}` 變數無來源 | 改由 `session.tool.called` 事件讀 `todowrite` 工具的 `input.todos`；未啟用該工具時 `{task}` 恆空 → 自動 fallback 到 `{firstMessage}` |

### 多實例隔離（V2 特有，必知）

**V2 會為「每個專案／location」各啟動一份 plugin 實例。** 實測同一個 plugin 在 4~5 個專案
各跑一次 `setup`，且**每個實例都訂閱到全域事件**。

若不篩選 session，所有實例會競爭同一個 session 的標題，最後寫入者勝出，
且用的是錯誤的 `projectName` fallback（實測標題變成 `2026-10-GothamCity` 而非訊息摘要）。

本移植版的處理：

```js
// session.created 事件以 projectID 比對，只認自己 location 的 session
if (myProjectID && data.projectID) return data.projectID === myProjectID
// 其他事件只處理 state 中「已追蹤」的 session
```

實測驗證：本專案與他專案的 session 各自被自己專案的實例命名，互不干擾。

## 為什麼不用「原生自動命名」

opencode 原生（`packages/opencode/src/session/prompt.ts` 的 `ensureTitle`）會在開新
session、僅有一則真實 user 訊息且仍是預設標題時，用 **small model** 總結第一則訊息取名。
已知問題：

- **issue #30662**：用 `opencode` 供應商模型（如 `opencode/big-pickle`）當 small model 時，
  自動命名**默默失敗**，標題停在 `New session - ...`。
- **issue #7523**：命名依賴 small model（預設類 `gpt-5-nano`）；該模型未開/壞掉就失效。

V2 的 `ctx.session.hook("title")` 是原生自動命名的攔截點（可設 `event.result` 跳過
small model 呼叫）。實測該 hook 在本機**不會觸發**（原生流程未走到 title 階段），
因此本移植版改走 `prompt` hook + 主動 `session.update`，不依賴原生流程。

所以本機（big-pickle）直接靠 plugin 方案；原生修法空白（`"small_model": "provider/modelID"`
指到可工作的模型）仍受 #30662 影響，不推薦。

## 替代方案比較（若需要「AI 語意總結」再考慮）

| 方案 | 機制 | Token | 需要 LLM |
|------|------|-------|---------|
| A. 原生 `small_model` 修法 | core 用 small model 總結第一則訊息 | ~1 call/session，極低 | ✅（big-pickle 下壞） |
| B. 本 skill 的 V2 移植版（已裝） | 規則式首句裁剪 | **0** | ❌ |
| C. opencode-session-summary | 每次閒置 + ≥4 新訊息，LLM 重生成一句；可設 `model` | 每 call 帶對話脈絡，長 session 可能數萬 Token | ✅ |
| D. opencode-autotitle | 關鍵字即時取名(🔍) + AI 精煉(✨)，自動挑最便宜模型；需 clone+build 放 `~/.config/opencode/plugins/` | 🔍0 + ✨0.5–2K/call | 🔍❌ + ✨✅ |

## 踩過的坑

| 坑 | 症狀 | 解法 |
|---|---|---|
| **在 `plugins` 陣列宣告相對路徑** | 本機 `~/.config/opencode/opencode.jsonc` 與 `D:\80-Opnecode\.opencode\opencode.jsonc` 是指向同一實體檔的**兩個 symlink**；相對路徑 `./plugins/X` 會依「宣告該條目的設定檔所在目錄」分別解析 → 同一 plugin 被**載入兩次**（一次路徑不存在、一次正常），`opencode plugin list` 出現重複列，options 只在其中一份生效 | **不要**在 config 宣告；改用全域 `~/.config/opencode/plugins/` 自動載入，選項內建於 plugin。若確實要用 options 覆寫，必須用**絕對路徑** |
| V1 plugin 在 V2 完全不載入 | `Plugin must export a default definition with an id and an effect or setup function`（`SchemaError(Expected object at ["default"])`） | 改成 `export default { id, setup(ctx) {...} }` |
| `ctx.session.list` / `ctx.session.remove` 型別有、runtime 沒有 | `TypeError: ctx.session.list is not a function` | 實測確認後不使用這些 API |
| 每專案一份 plugin 實例 | 標題被其他專案的實例改寫成錯誤的 projectName | 以 `session.created` 的 `projectID` 篩選，只處理自己 location 的 session |
| `todowrite` 工具未啟用 | `{task}` 變數無來源 | 樣板用 `{firstMessage}`；或啟用 experimental todo flag |

## 附錄：端到端驗證腳本

```javascript
// 需先取得 service.json 的密碼做 Basic auth
import fs from "node:fs"
const svc = JSON.parse(fs.readFileSync(process.env.USERPROFILE + "\\.config\\opencode\\service.json", "utf8"))
const auth = "Basic " + Buffer.from("opencode:" + svc.password).toString("base64")
const base = `http://127.0.0.1:${svc.port}`
const H = { "content-type": "application/json", authorization: auth }
const DIR = "D:\\80-Opnecode\\Projects\\OpenCode_skill"

const cr = await fetch(`${base}/api/session`, {
  method: "POST", headers: H,
  body: JSON.stringify({ title: "New session - ...", location: { directory: DIR } }),
})
const sid = (await cr.json()).data.id
await fetch(`${base}/api/session/${sid}/prompt`, {
  method: "POST", headers: H,
  body: JSON.stringify({ text: "請幫我分析這個 repo 並整理成 Markdown 報告" }),
})
await new Promise((r) => setTimeout(r, 14000))
const g = await fetch(`${base}/api/session/${sid}`, { headers: { authorization: auth } })
console.log("標題:", (await g.json()).data.title)   // 應為訊息摘要，非 "New session - ..."
await fetch(`${base}/api/session/${sid}`, { method: "DELETE", headers: { authorization: auth } })
```

## Deliverables checklist

- [x] `opencode-session-auto-name/plugin/index.js` 存在於本 repo（唯一真實來源）
- [x] 已部署到 `<USERPROFILE>\.config\opencode\plugins\opencode-auto-name\`
- [x] `opencode plugin list` 只出現**一筆** `opencode-auto-name`（ID 正確）
- [x] `opencode.jsonc` 的 `plugins` 陣列**不**宣告此 plugin（避免 symlink 重複解析）
- [x] V1 npm 套件已 `npm uninstall`，設定中不再引用
- [x] 端到端驗證：新 session 標題變成訊息摘要；他專案 session 不受影響


# OpenCode Usage Monitor

唯讀監測 OpenCode 的用量、額度與本機資源佔用，並產生專業 HTML 儀表板。

- **技能目錄**：`<USERPROFILE>\.config\opencode\skills\opencode-usage\`
- **產出目錄**：`<USERPROFILE>\.local\share\opencode-usage\`
- **更新頻率**：每 10 分鐘（Windows 排程器，零常駐記憶體）
- **設計原則**：**全程唯讀**。不修改 `opencode.db`、`auth.json`、任何 OpenCode 設定（唯一例外是你主動按下的清理按鈕）

---

## 路徑須知

> 本檔案中的絕對路徑來自**撰寫時的機器**，在其他機器上不一定存在。
>
> - skills 目錄以 `~/.config/opencode/skills/` 為準（PowerShell 用 `Join-Path $env:USERPROFILE ".config\opencode\skills"` 推導）
> - 專案／輸出／暫存路徑先確認存在；找不到就問使用者實際路徑，不要自行猜測或建立
> - 出現的 `<USER_2>` 等前綴屬**操作紀錄範例**，不是可依賴的事實

## 目錄

1. [快速開始](#1-快速開始)
2. [架構總覽](#2-架構總覽)
3. [資料來源](#3-資料來源)
4. [指標定義與計算方式](#4-指標定義與計算方式)
5. [資料庫膨脹分析與門檻設定](#5-資料庫膨脹分析與門檻設定)
6. [花費計算模型](#6-花費計算模型)
7. [Telegram 告警設定](#7-telegram-告警設定)
8. [安裝 10 分鐘排程](#8-安裝-10-分鐘排程)
9. [設定檔完整說明](#9-設定檔完整說明)
10. [儀表板設計](#10-儀表板設計)
11. [清除暫存資料（Maintenance）](#11-清除暫存資料maintenance)
12. [疑難排解](#12-疑難排解)
13. [擴充方式](#13-擴充方式)
14. [技術筆記（學習用）](#14-技術筆記學習用)

---

## 1. 快速開始

```powershell
$S = "$env:USERPROFILE\.config\opencode\skills\opencode-usage"

# 產生快照 + 重新產生儀表板
python "$S\collect.py"

# 終端機輸出 markdown 報告
python "$S\collect.py" --report

# 預覽可回收空間（唯讀）
python "$S\cleanup.py" survey

# 測試 Telegram 連線
python "$S\alert.py" --test-telegram

# 開啟儀表板
Start-Process "$S\dashboard-latest.html"
```

在 opencode 對話中可直接用自然語言觸發，例如：
「我今天用了多少 token？」「opencode 佔多少磁碟？」「重新產生用量儀表板」「opencode 額度還剩多少？」

---

## 2. 架構總覽

```
┌──────────────────── 排程器（每 10 分鐘，零常駐）────────────────────┐
│                                                                    │
│  collect.py ──► 唯讀開啟 opencode.db (mode=ro)                      │
│      │             ├─ session   彙整：sessions / tokens / cost       │
│      │             ├─ message   逐次請求：請求數 / 滾動視窗 / 每小時   │
│      │             ├─ 磁碟掃描  db / log / snapshot / tool-output     │
│      │             ├─ Get-Process OpenCode  → CPU / RSS             │
│      │             ├─ opencode.log（僅讀 tail 4 MB）→ 429 / 錯誤     │
│      │             └─ 額度 API（30 分快取，失敗靜默降級）            │
│      │                                                                │
│      ├──► snapshot.json      最新完整指標                             │
│      ├──► history.jsonl      每 10 分鐘一列（趨勢用，上限 20,000 列） │
│      └──► dashboard.html     資料注入後的單檔自帶儀表板               │
│                                                                    │
│  alert.py ──► 讀 snapshot.json → 門檻比對 → 去重 → 通知              │
│      ├──► Windows 通知（BurntToast / 系統氣球）                      │
│      ├──► Telegram Bot                                          │
│      └──► Webhook（n8n / Slack / 任意）                             │
│                                                                    │
│  cleanup.py ◄── 儀表板按鈕經 ocusage:// 協定呼叫（見第 11 節）        │
└────────────────────────────────────────────────────────────────────┘
```

**為什麼不用常駐 Web 伺服器？** 實測常駐 `python http.server` 需 40–60 MB RAM，且要管理開機自啟與埠號衝突；而排程式採集每次喚醒僅 **0.3–0.6 秒**、結束後記憶體歸零。儀表板用 `<meta http-equiv="refresh" content="600">` 達成 10 分鐘自動更新，使用者完全無感。

**按鈕怎麼在沒有伺服器的情況下執行本機程式？** 靠 Windows 的 `ocusage://` 自訂協定（註冊於 `HKCU\Software\Classes`，免管理員權限）。瀏覽器點擊 `<a href="ocusage://safe">` 會啟動登錄的處理器，執行完把結果寫入 `cleanup.log` 再重新開啟儀表板。

---

## 3. 資料來源

| 來源 | 提供的資料 | 讀取方式 |
|---|---|---|
| `~/.local/share/opencode/opencode.db` | `session`、`message` 表 | `file:...?mode=ro` **唯讀** URI |
| `~/.local/share/opencode/log/opencode.log` | 串流錯誤、429 限流 | 二進位 seek 讀 **最後 4 MB** |
| `~/.local/share/opencode/auth.json` | openrouter / agnes 金鑰 | 僅供額度 API 探測 |
| `Get-Process OpenCode` | 7 個行程的 CPU 秒數與 RSS | PowerShell 子行程 |
| 磁碟掃描 | 資料目錄各子目錄大小 | `os.walk` |

### Schema 對應（實測本機版本）

```sql
session(  id, title, directory, model, cost,
          tokens_input, tokens_output, tokens_reasoning,
          tokens_cache_read, tokens_cache_write,
          summary_files, summary_additions, summary_deletions,
          time_created, time_updated )

message(  id, session_id, time_created, data )  -- data 為 JSON
part(     id, message_id, session_id, time_created, data )
```

`message.data` 的實際結構（僅 assistant 轉向有 tokens/cost）：

```json
{
  "role": "assistant",
  "providerID": "opencode",
  "modelID": "big-pickle",
  "variant": "low",
  "cost": 0,
  "tokens": { "input": 0, "output": 0, "reasoning": 0,
              "cache": { "read": 0, "write": 0 } }
}
```

> **`event` 表（172,529 列）永遠不掃描** —— 它佔 2.38 GB 且 `data` 無查詢需求，掃一次就要好幾秒。

---

## 4. 指標定義與計算方式

### 4.1 Tokens（本機實測值）

| 指標 | 來源 | 說明 |
|---|---|---|
| `tokens_input` | `SUM(session.tokens_input)` | 實際送給模型的輸入 |
| `tokens_output` | `SUM(session.tokens_output)` | 模型產出 |
| `tokens_reasoning` | `SUM(session.tokens_reasoning)` | 思考型模型內部推理 |
| `tokens_cache_read` | `SUM(session.tokens_cache_read)` | 命中提示詞快取 |
| `tokens_cache_write` | `SUM(session.tokens_cache_write)` | 寫入快取（付費才有） |
| `tokens.total` | 以上五項相加 | **注意：這不是實際付費量**，快取 token 單價通常低 10 倍 |
| `cache_hit_rate` | `cache_read / (input + cache_read)` | 快取命中率，越高代表用量越省 |

本機現況：input 33.2M / output 4.58M / reasoning 0.59M / cache_read 472.0M，**命中率 93.4%**。

### 4.2 Requests（請求數）

只用 `role='assistant'` 的 message，因為 user 訊息不產生模型呼叫：

```sql
SELECT COUNT(*) FROM message
WHERE json_extract(data,'$.role') = 'assistant';
```

這是「真正打向上游模型的次數」，比 session 數更能反映額度消耗。分鐘級資料不存在於任何表，所以**每小時**統計以 `time_created` 分桶取最近 24 小時。

### 4.3 限時管制：從伺服器原始碼還原的真實機制

> 這一節先前只靠單一 GitHub issue 推論，結論有誤。以下是從 **OpenCode 伺服器原始碼**（`dev` 分支）還原的事實。

```ts
// packages/console/app/src/routes/zen/util/ipRateLimiter.ts
const limits       = Subscription.getFreeLimits()          // → limits.dailyRequests
const dailyLimit   = rateLimit ?? limits.dailyRequests     // 每模型可覆寫
const isDefaultModel = headersExist && !rateLimit
const dailyInterval = rateLimit ? `${YYYYMMDD}${modelId.substring(0,2)}` : YYYYMMDD
const lifetimeKey  = buildRateLimitKey("ip", ip)
const dailyKey     = buildRateLimitKey("ip", ip, dailyInterval)
isNew = isDefaultModel && lifetimeCount < dailyLimit * 7
if ((isNew && dailyCount >= dailyLimit * 2) || (!isNew && dailyCount >= dailyLimit))
  throw new FreeUsageLimitError(...)
```

```ts
// packages/console/core/src/subscription.ts
export const getFreeLimits = () => getLimits()["free"]
const json = JSON.parse(Resource.ZEN_LIMITS.value)   // ← 數值存在「資源」裡，不在 git
```

#### 五個關鍵事實

| # | 事實 | 影響 |
|---|---|---|
| 1 | **計數依「IP 位址」，不是帳號** | 換網路（VPN、公司 Proxy、寬頻行動網路）就重置。issue #34344 記錄了 VPN 輪換可無限使用的漏洞 |
| 2 | **UTC 日界**（`buildYYYYMMDD` 用 `toISOString`） | 每日 **08:00（台灣時間）** 重置，不是本地午夜 |
| 3 | **有自訂 `rateLimit` 的模型 → 獨立桶** | key 為 `YYYYMMDD + modelId 前兩碼`，上限也是該模型自己的值；**共用桶**只有一組 |
| 4 | **新 IP 享雙倍**（`lifetime < dailyLimit * 7`） | 終身次數 < 1400 時，上限是 `200 × 2 = 400`/日 |
| 5 | **數值在 `Resource.ZEN_LIMITS`（伺服器端）** | 不在原始碼裡，可隨時被改動。**200 是文件／社群觀察值，不是可查證的常數** |

#### 為什麼「200 次/日」不足夠精確

| 變因 | 影響範圍 |
|---|---|
| 是否新 IP | 上限在 **200 與 400** 之間跳動 |
| 公司 Proxy 出口 IP 變動 | 每次都像新使用者 → 一直拿 400 |
| 用了哪些免費模型 | 若 `space-bunny-free` 等帶自訂 `rateLimit`，則獨立計數、上限可能 >200 |
| 時區 | 08:00 重置，跨日時的推算會錯 |

#### 本工具的處理方式

```
provider = "opencode"（Zen）才計入           其他供應商（agnes / openrouter）不影響此限流
UTC 日界（對齊伺服器 buildYYYYMMDD）        顯示 utc_day_start
free_daily_base = 200、free_daily_cap = 400  200 = dailyRequests，400 = 新 IP 雙倍層
cap_is_estimate = true                       明確標示為推估，非官方數值
```

**目前設定：`free_daily_cap = 400`**，因為本機實測在超過 200 次後仍可正常使用（符合「該 IP 仍在雙倍層」或「模型有獨立桶」的推論），若當時設 200 就會長期誤報。

#### 指標

| 指標 | 定義 |
|---|---|
| `requests_today` | 自 UTC 日界起、provider=opencode 的 assistant 請求數 |
| `window_1h / 5h / 24h` | 滾動視窗，同樣只算 Zen |
| `lifetime` | 本機觀察到的 Zen 終身請求數（與伺服器的 per-IP 計數器不同，僅供參考） |
| `models_today` | 今日各 Zen 模型的請求數與佔比 → 判斷是否有模型走獨立桶 |
| `blocked_events` | 24 小時內 429 事件數 → **唯一實證**是否被擋 |

#### 告警門檻（已依你要求設定）

```
quota_warn_pct = 80  →  320 次   warn
quota_crit_pct = 95  →  380 次   crit
blocked_events > 0   →  crit（代表真的被擋，無論計數多少）
```

若要改回 200 基準，把 `oc-usage.json` 的 `free_daily_cap` 設為 200 即可。

**沒有官方 API 可查真實剩餘量** —— 限流在伺服器端且依 IP，本工具是「本地計數 + 429 實證」的近似。若要精確值，只能在瀏覽器登入 opencode.ai 觀察前端顯示。

### 4.4 資源指標

- `processes.rss_mb` = 所有 `OpenCode.exe` 的 WorkingSet 總和（本機 7 個行程 = 1,299 MB，這是 Electron 的正常量級）
- `processes.cpu_s` = 累計 CPU 秒數（單調遞增，代表生命週期總量而非瞬時值）
- `disk._total_mb` = 資料目錄下所有檔案總和

---

## 5. 資料庫膨脹分析與門檻設定

### 實測組成

| 來源 | 列數 | 平均每列 | 佔用 | 佔比 |
|---|---:|---:|---:|---:|
| `event` | 172,529 | 13.8 KB | **~2.38 GB** | 82% |
| `part` | 29,626 | 10.8 KB | ~320 MB | 11% |
| `message` | 7,119 | 2.9 KB | ~21 MB | 0.7% |
| 其他（索引 / 頁面 / 快照） | — | — | ~200 MB | 6% |
| **合計** | | | **2,909 MB** | |

`PRAGMA freelist_count = 0` → **沒有空洞，執行 `VACUUM` 完全沒用**，純粹是真實資料量成長。

### 成長率

session 資料涵蓋 **47 天**（`time_created` 最小/最大值相差 4.1e9 ms）：

```
event    2,380 MB / 47 天 ≈ 50.6 MB/天
part       320 MB / 47 天 ≈  6.8 MB/天
message     21 MB / 47 天 ≈  0.4 MB/天
──────────────────────────────────────
合計                        ≈ 58 MB/天  ≈ 1.7 GB/月
```

### 5.2 資料庫解剖（`opencode.db` 2,912.5 MB 裡裝什麼）

以 `PRAGMA page_size / page_count / freelist_count` 加上各表 `sum(length(data))` 實測：

| 來源 | 佔用 | 佔比 |
|---|---:|---:|
| **`event` 表** | **2,269 MB** | **78%** |
| `part` 表 | 306 MB | 10.5% |
| `message` 表 | 20 MB | 0.7% |
| 索引 / overflow 頁 / 其他表 | ~337 MB | 11.6% |

#### `event` 是事件溯源（event sourcing）存儲

| event type | 筆數 | 說明 |
|---|---:|---|
| `message.part.updated.1` | **138,525** | 每次串流更新都存一筆**完整快照** |
| `message.updated.1` | 27,499 | 訊息狀態變更 |
| `session.updated.1` | 7,455 | Session 狀態 |
| `session.created.1` | 98 | 建立 |

平均每筆 **13.7 KB**，單筆最大 **14.4 MB**。成因是模型串流吐字時，每收到一個片段就把**整段已累積的文字重寫一次**——第 100 次更新存的是完整 100 段的內容。這是 O(n²) 的膨脹模式。

**關鍵洞察：這些是純冗餘。** 當前狀態已完整存在於 `message` / `part` 表，`event` 只是供「重播 / fork / undo / 分享連結」使用的歷史。刪掉它們可回收約 78% 的資料庫，代價是失去這些歷史功能。

#### 依年齡分布

| 年齡 | Sessions | event | part | 合計 |
|---|---:|---:|---:|---:|
| 0–7 天 | 17 | 163 MB | 64 MB | 227 MB |
| 8–14 天 | 8 | 229 MB | 200 MB | 429 MB |
| 15–30 天 | 31 | 272 MB | 19 MB | 291 MB |
| **31–60 天** | **42** | **1,605 MB** | 23 MB | **1,628 MB（56%）** |
| 60 天以上 | 0 | 0 | 0 | 0 |

**56% 的資料集中在 31–60 天前的 42 個 session。**

#### 不同保留期限的回收量（實測）

| 保留 | 刪除 session 數 | 回收 |
|---|---:|---:|
| 7 天 | 81（83%） | 極多，但會失去多數對話 |
| 14 天 | 73（74%） | 更多 |
| 30 天 | 42（43%） | **1.57 GB** |
| 45 天 | 6（6%） | 995 MB |

> 實測指令：`python cleanup.py purge --days 45`（DRY RUN，不動資料）

### 5.3 門檻怎麼訂

公式：

```
門檻 = 目前 MB + 預期保留天數 × 58 MB/天
```

| 預期保留 | 建議門檻 | 觸發時間 |
|---|---:|---|
| 30 天 | 4,650 MB | 約 30 天後 |
| 60 天 | 6,390 MB | 約 60 天後 |
| 90 天 | 8,130 MB | 約 90 天後 |

目前採 **warn 4096 MB / crit 8192 MB**（對應約 19 天 / 90 天），是偏保守的設定，適合「想及早知道」而非「不想被打擾」。

**注意**：你最初提出的 1024 MB 會導致永久告警（當時已 2,909 MB），所以不採用。

### 真正該做的處置

`event` 表是主因，而它由 `ON DELETE CASCADE` 從 `session` 刪除衍生。**封存舊 session 才會真正釋放空間** —— 這正是第 11 節 Maintenance 面板的「封存舊 session」功能。

---

## 6. 花費計算模型

系統提供兩個獨立數字，不可混用：

### 6.1 `cost` — 實際計費（權威）

直接讀取 OpenCode 從上游回報的真實費用，逐 session 加總。**免費模型回傳 0，這是真實值不是估算。**

本機 98 個 session 全部使用免費模型（`big-pickle`、`space-bunny-free`、`mimo-v2.5-free`、`openrouter/free`、`agnes-*`），故 `cost` 恆為 **$0.0000**。

### 6.2 `cost_est` — 估算（僅付費模型有意義）

當 session 的 `(provider, model)` 命中 `PRICES` 表時才計算：

```
cost_est = input/1e6 × price_in
         + output/1e6 × price_out
         + cache_read/1e6 × price_cache
```

未列入 `PRICES` 的模型一律視為 $0（寧可低估也不虛報）。新增付費模型時把單價加進 `collect.py` 的 `PRICES` 字典即可：

```python
PRICES = {
    ("openrouter", "openai/gpt-5.5"): (1.05, 8.40, 0.105),   # (輸入, 輸出, 快取讀取)
}
```

### 6.3 門檻怎麼定

`cost_warn_usd` 目前設 **$1**。理由：以 GPT-5.5 級單價估算，一天中等強度使用約 3–5M input + 0.5M output ≈ **$7**，所以 $1 是「異常放量」的早期訊號。

原本的 $5 在**免費模型時代永不觸發**，形同虛設，故調低為 $1。若你刻意在跑大量付費批次，可調回 $5–$20。

---

## 7. Telegram 告警設定（token 完全本機加密）

> **設計原則：token 絕不離開這台電腦的明文形式。** 不寫入設定檔、不寫入 `snapshot.json`、不出現在 `dashboard.html`、不進 git、不經過任何雲端或模型服務。

### 7.1 建立機器人

1. 對 **@BotFather** 傳 `/newbot`，依提示取名 → 取得 **Bot Token**（`123456789:AAE...`）
2. 開啟你的 bot 對話視窗，傳一句 `/start`（Telegram API 必須先有對話才能取得 chat_id）
3. 取得 **Chat ID**
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
   回傳 JSON 中找 `"chat":{"id": 123456789}`（私聊為正數、群組為負數）

### 7.2 本機設定（遮罩輸入 + DPAPI 加密）

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.config\opencode\skills\opencode-usage\set_telegram.ps1"
```

腳本行為：

| 步驟 | 說明 |
|---|---|
| `Read-Host -AsSecureString` | **輸入內容完全不顯示**，也不會進入 PowerShell 歷史或日誌 |
| 格式驗證 | 必須符合 `^\d+:[A-Za-z0-9_-]+$`，否則拒絕儲存 |
| `ConvertFrom-SecureString` | 以 **DPAPI（使用者範圍）** 加密，密鑰綁定你的 Windows 帳號 |
| `icacls /inheritance:r` | ACL 移除繼承，只保留你的帳號可讀寫 |
| 落地檔 | `~/.local/share/opencode-usage/telegram.enc` |

**重要：請在本機終端機自己執行，不要把 token 貼到任何聊天視窗**（那會送給模型供應商）。這也是這個工具的設計前提。

檢視 / 停用：

```powershell
... \set_telegram.ps1 -Status     # 顯示 1234567***(46 chars, DPAPI-encrypted)
... \set_telegram.ps1 -Disable    # 刪除加密檔並停用
```

### 7.3 測試

```powershell
python "$env:USERPROFILE\.config\opencode\skills\opencode-usage\alert.py" --test-telegram
```

### 7.4 執行時的解密流程

```
alert.py 執行
   ├─ 檢查環境變數 TELEGRAM_BOT_TOKEN（有就用，優先序最高）
   └─ 否則讀 telegram.enc
        └─ powershell -Command "ConvertTo-SecureString + SecureStringToBSTR"
             └─ 明文只存在於子行程 stdout 與本行程記憶體變數
                  └─ 用完即棄，永不寫入任何檔案
```

若解密失敗（換帳號、還原備份、檔案損毀），`alert.py` 會印出 `telegram: skipped (decrypt-failed)` 並**跳過傳送**，不會退化成任何明文處理。

### 7.5 防止 token 洩漏到儀表板的三道防線

因為 `collect.py` 每 10 分鐘會把 `snapshot.json` 的 config **注入 `dashboard.html`**（任何能開啟該 HTML 的人都能看），所以：

1. `sanitize_config()` 剝除 `telegram`、`webhook`，以及任何鍵名含 `token` / `key` 的項目
2. token 從不進入 `oc-usage.json`（它只存在於 DPAPI 檔案）
3. `.gitignore` 排除 `*.enc` 與 `dashboard-latest.html`

已實測驗證：`dashboard.html` 中不含 `sk-or`、`sk-WQQ`、`TELEGRAM_BOT_TOKEN` 等任何金鑰字樣（出現的 `token` 皆為 `tokens_input` 之類的指標名）。

### 7.6 訊息格式

```
*OpenCode Usage*  `2026-09-27T17:45:26+08:00`
sessions `99` · requests today `102/200` (51.0%)
tokens `516,370,636` · cache hit `93%`
db `2909 MB` · store `2953 MB` · app `1299 MB`
cost `$0.00` (est `$0.00`)
🔴 *FreeUsageLimitError (429)* — 5 rate-limit events in 24h …
```

### 7.7 去重機制

`alert-state.json` 記錄已推送的 `level:title` 集合。只有**新增告警或等級變化**才推送，狀態相同則靜默 —— 不會每 10 分鐘轟炸。恢復正常時因為告警清單變空，同樣會觸發一次狀態轉換。

---

## 8. 安裝 10 分鐘排程

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.config\opencode\skills\opencode-usage\install_task.ps1"
```

建立兩個工作：

| 工作 | 內容 |
|---|---|
| `OpenCodeUsage-Collect` | 執行 `collect.py`，重建儀表板 |
| `OpenCodeUsage-Alert` | 執行 `alert.py --quiet-ok`，評估並推送 |

自訂間隔與移除：

```powershell
powershell -ExecutionPolicy Bypass -File ...\install_task.ps1 -IntervalMinutes 15
powershell -ExecutionPolicy Bypass -File ...\install_task.ps1 -Uninstall
```

排程器設定含 `AllowStartIfOnBatteries`、`DontStopIfGoingOnBatteries`、`MultipleInstances IgnoreNew`，避免休眠時堆積重複執行。

---

## 9. 設定檔完整說明

位置：`<USERPROFILE>\.config\opencode\oc-usage.json`

| 鍵 | 預設 | 說明 |
|---|---:|---|
| `db_warn_mb` | 4096 | DB 超過此值產生 warn |
| `db_crit_mb` | 8192 | DB 超過此值產生 crit（紅色） |
| `idle_warn_min` | 240 | 超過此分鐘無 session 活動即提醒 |
| `cost_warn_usd` | 1.0 | 估算花費超過此值即提醒 |
| `free_daily_cap` | 200 | 免費層每日請求上限（FreeUsageLimitError）；僅用於算百分比 |
| `credits_enabled` | true | 是否探測供應商額度 API |
| `credits_ttl_min` | 30 | 額度 API 快取分鐘數，避免每 10 分鐘打一次 |
| `toast` | true | 是否顯示 Windows 通知 |
| `telegram` | object | Telegram 設定（見第 7 節） |
| `webhook` | `""` | 任意 webhook（n8n / Slack / 任意） |

---

## 10. 儀表板設計

版型檔：`templates/dashboard.html`（單一 HTML，Chart.js 走 CDN）

**版面順序**

1. **Header** — 主機名、產生時間、狀態燈（>60 分鐘轉黃）、Refresh、深淺色切換（localStorage 記住）
2. **Alerts** — 門檻告警；全數正常時顯示綠色 "All clear" 摘要列
3. **Free-tier quota**（最上方的圖表區）— 200/日 環圖 + 進度條 + 429 實證狀態 + 上限來源說明
4. **Requests per hour** — 24 小時長條 + 1h/5h/24h/最忙小時 四格滾動視窗
5. **Overview** — 9 張 KPI 卡：總 tokens、請求數、cache read、sessions、磁碟佔用、程式記憶體、額度使用 %、滾動 5 小時視窗、花費
6. **Maintenance / Database composition** — 清理按鈕 + DB 組成推估表
7. **圖表** — token 組成環圖、模型橫向長條、磁碟佔比環圖
8. **表格** — Models（含佔比條）、Provider credits（degraded 標記）、最近 12 個 session、磁碟/行程

**設計語言**：深色為主、雙 radial-gradient 漸層背景、卡片 1px 頂部色條、數字用 `tabular-nums` 對齊、等寬數字不跳動、每張卡專屬強調色。

**資料注入機制**：`collect.py` 讀取版型檔，將 `/*__DATA__*/null` 替換成 `snapshot.json` 內容後輸出成品。選這招而非 `fetch()` 是因為 `file://` 協議下 fetch 會被 CORS 阻擋，注入則完全離線可用（只需 CDN 取 Chart.js）。

---

## 11. 清除暫存資料（Maintenance）

儀表板提供三顆按鈕，透過 **`ocusage://` 自訂協定**在本機執行 `cleanup.py`，**不需要常駐伺服器**。協定註冊在 `HKCU`（免管理員權限）：

```powershell
powershell -ExecutionPolicy Bypass -File ...\register_protocol.ps1     # 註冊
powershell -ExecutionPolicy Bypass -File ...\register_protocol.ps1 -Uninstall
```

### 三個等級

| 按鈕 | 動作 | 可回收 | 風險 |
|---|---|---:|---|
| **安全清理** | 輪替 `opencode.log`（保留最後 2 MB）、刪除過期 `tool-output/`、WAL checkpoint、修剪 `history.jsonl` | ~18 MB | 無 |
| **僅 WAL checkpoint** | 只回收 `-wal` 暫存 | ~4 MB | 無 |
| **封存舊 session** | 刪除 N 天未活動的 session + `VACUUM` | **~1.57 GB** | **永久刪除對話紀錄** |

前兩顆按鈕是 `<a href="ocusage://safe">`，點下去瀏覽器會問「是否開啟外部應用程式」→ 同意後開一個短暫主控台視窗執行，結果寫入 `~/.local/share/opencode-usage/cleanup.log`，並自動重新開啟儀表板。

### 為什麼「封存舊 session」不做成按鈕

按鈕無法承載「輸入 PURGE 確認」這種互動，而且它會**永久刪除你的對話歷史**。所以它只提供說明與可複製的指令，必須在終端機手動執行：

```powershell
# 1. 先預覽（唯讀，不會動任何資料）
python "$env:USERPROFILE\.config\opencode\skills\opencode-usage\cleanup.py" purge --days 30

# 2. 確認後執行（建議務必加 --backup）
python "$env:USERPROFILE\.config\opencode\skills\opencode-usage\cleanup.py" purge `
  --days 30 --apply --yes PURGE --backup "$env:USERPROFILE\opencode-backup.db"
```

`--yes PURGE` 這道令牌是刻意的：沒有它 `cleanup.py` 直接拒絕執行（exit code 3）。

### 實測輸出

```
OpenCode cleanup survey
------------------------------------------------------------------------------
  opencode.log                         12.8 MB
    rotate, keep last 2 MB
    reclaim 10.8 MB   risk: none
  tool-output/                          2.9 MB
    delete 13 cached tool results older than 30 days
    reclaim 2.9 MB     risk: low - only affects re-reading old tool output
  opencode.db-wal                       4.0 MB
    WAL truncate (checkpoint)
    reclaim 4.0 MB     risk: none
! opencode.db (purge old sessions)     2.84 GB
    delete sessions untouched for 30+ days, then VACUUM
    reclaim 1.57 GB    risk: DESTRUCTIVE - permanently removes conversation history
------------------------------------------------------------------------------
safe cleanup reclaims : 17.7 MB   (no data loss)
session purge reclaims: 1.57 GB   (DESTRUCTIVE, CLI only)
total available       : 1.58 GB
```

### 為什麼安全清理只能回收 18 MB

因為 `freelist_count = 0`。`VACUUM` 的作用是「把已刪除但仍佔空間的頁面回收並重整檔案」；你的資料庫沒有任何空洞，所以**再怎麼 VACUUM 都不會變小**。真正能讓數字變小的只有刪掉資料本身，而唯一有價值的資料就是舊的 session（其 `event`/`part`/`message` 會因 `ON DELETE CASCADE` 連帶刪除，之後 `VACUUM` 就能把 1.57 GB 真正還給檔案系統）。

### 定期自動清理（選用）

```powershell
$py = (Get-Command python).Source
$s  = "$env:USERPROFILE\.config\opencode\skills\opencode-usage\cleanup.py"
$a = New-ScheduledTaskAction -Execute $py -Argument "`"$s`" safe --apply --days 14"
$t = New-ScheduledTaskTrigger -Weekly -At 4am -DaysOfWeek Sunday
Register-ScheduledTask -TaskName 'OpenCodeUsage-Cleanup' -Action $a -Trigger $t `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable) -Force
```

只跑 `safe` 等級（不碰 session），每週日凌晨 4 點。

---

## 12. 疑難排解

| 症狀 | 原因與處理 |
|---|---|
| 額度欄位全顯示 `unknown` | **預期行為**。OpenRouter 金鑰回 401、Agnes 無公開端點、Zen 免費層無 API。採集器會靜默降級，不視為錯誤 |
| 按了清理按鈝沒反應 | 尚未註冊協定，執行 `register_protocol.ps1`；結果可看 `~/.local/share/opencode-usage/cleanup.log` |
| 清理後儀表板沒更新 | 協定處理器會自動重開分頁；若沒開，手動按 Refresh |
| `opencode.db not found` | 換機或首次啟動前執行。確認 `~/.local/share/opencode/opencode.db` 存在 |
| 儀表板顯示 `loading…` | CDN 無法連線。改用本機 Chart.js：下載後把 `<script src>` 換成相對路徑 |
| 限流事件數異常偏高 | 已修正過兩個誤判來源：log 時間戳中的 `.429`、以及監控指令自身的權限回顯。現在只計 `level=ERROR/WARN` 且 24 小時內、且排除 `message=evaluated permission` 的行 |
| `telegram not configured` | `enabled` 沒開，或缺 `bot_token` / `chat_id` |
| 排程沒在跑 | 用 `Get-ScheduledTask -TaskName 'OpenCodeUsage-*'` 檢查；用 `Get-ScheduledTaskInfo` 看上次執行結果 |
| 儀表板沒更新 | 手動跑 `python ...\collect.py` 看是否報錯；HTML 內含 `<meta http-equiv="refresh" content="600">`，開著的分頁會自動重載 |

---

## 13. 擴充方式

- **新增付費模型單價** → 編輯 `collect.py` 的 `PRICES` 字典
- **新增指標** → 在 `build()` 內加函式，欄位會自動出現在 `snapshot.json`，KPI 卡在 `dashboard.html` 的 `cards` 陣列加一筆
- **改變更頻率** → 排程器觸發器的 `RepetitionInterval`（改後需重新登錄工作）
- **接 n8n** → 設 `OPENCODE_ALERT_WEBHOOK` 環境變數，收到的 JSON 格式：
  ```json
  {"source":"opencode-usage","generated_at":"...","alerts":[{"level":"warn","title":"...","detail":"..."}],
   "summary":{"db_mb":2909,"requests_today":102,"rss_mb":1299}}
  ```
- **GitHub 同步** → 可用既有的 `github-skill-sync` skill 將本目錄推上 `yd7148/OpenCode_skill`

---

## 14. 技術筆記（學習用）

### 14.1 為什麼 SQLite 要用唯讀 URI

```python
sqlite3.connect("file:/path/to.db?mode=ro", uri=True)
```

普通連線會建立 WAL 與 shared memory 檔，等於**寫入**資料庫。監控工具必須保證零副作用，故強制 `mode=ro`。副作用是讀不到尚未 checkpoint 的 WAL 內容（`mode=ro` 仍可讀 WAL，但不會觸發 checkpoint）。

### 14.2 善用 JSON1 擴充

SQLite 內建 JSON1，不必把 7,119 列撈回 Python 解析：

```sql
json_extract(data,'$.role') = 'assistant'
json_extract(data,'$.tokens.input')
```

這讓統計完全在 C 層完成，是本工具能在 0.3 秒內跑完的關鍵。若你的 SQLite 未編譯 JSON1，會報 `no such function: json_extract` —— 需改用 Python 端解析（較慢但相容）。

### 14.3 大檔案只讀 tail

`opencode.log` 會無限成長（本機 12.8 MB 且仍在長）。讀全文會愈來愈慢，因此：

```python
with open(path, "rb") as fh:
    fh.seek(0, 2)          # 跳到結尾
    fh.seek(max(0, fh.tell() - 4*1024*1024))
    tail = fh.read().decode("utf-8", "replace")
```

二進位模式 + `seek` 是關鍵（文字模式 `seek` 只接受 `whence=0` 的位移量）。

### 14.4 `history.jsonl` 為什麼用 JSONL

每行一個 JSON 物件，是日誌型資料的標準做法：append 是 O(1) 不需重寫、損壞時只需丟棄單行、Python 端 `readlines()[-72:]` 直接取最近 N 筆。程式內並保留 20,000 列上限並在超過時截斷到 10,000 列，避免無限成長。

### 14.5 排程器 vs 常駐服務的取捨

| | 排程式（本工具） | 常駐 http.server |
|---|---|---|
| RAM | 0（結束即釋放） | 40–60 MB |
| 喚醒延遲 | 0.3–0.6 s | 0 |
| 維護 | 無（無開機自啟、無埠號） | 需處理 |
| 排程器開機補跑 | ✅ `StartWhenAvailable` | — |

對「每 10 分鐘看一次」這種低頻需求，排程式在資源與維護成本上都明顯勝出。

### 14.6 瀏覽器按鈕如何執行本機程式：`ocusage://`

一般網頁無法執行本機指令，但 Windows 支援在 `HKCU\Software\Classes\<scheme>\shell\open\command` 註冊自訂協定。使用者（而非系統管理員）即可註冊：

```powershell
New-Item -Path 'HKCU:\Software\Classes\ocusage' -Force
New-ItemProperty -Path 'HKCU:\Software\Classes\ocusage' -Name 'URL Protocol' -Value ''
New-ItemProperty -Path 'HKCU:\Software\Classes\ocusage\shell\open\command' `
  -Name '(Default)' -Value '"C:\...\python.exe" "C:\...\cleanup.py" "%1" --apply'
```

之後 HTML 裡的 `<a href="ocusage://safe">` 就會啟動它。注意事項：
- 需要 `URL Protocol` 這個空值鍵存在，瀏覽器才會把它當成外部協定
- `%1` 是完整 URL，`cleanup.py` 用 `urlparse` 拆出 `netloc`（即 `safe`）與 query（`?days=30`）
- 瀏覽器會跳「是否開啟外部應用程式」確認框，這是安全機制，不是 bug
- **安全性**：協助處理器絕不能帶 `--yes PURGE`，否則網頁就能刪你的對話紀錄。`cleanup.py` 的設計是沒有令牌就拒絕執行 purge

### 14.7 告警去重的設計

狀態機只需存 `level:title` 的集合：

```python
current = sorted(f"{a['level']}:{a['title']}" for a in alerts)
new = [a for a in alerts if f"{a['level']}:{a['title']}" not in state["fired"]]
```

比對的是「等級 + 標題」而非完整內容，因此細節數字變動（例如 2909 → 2950 MB）**不會**重複轟炸，但等級升級（warn → crit）**會**。

### 14.8 `VACUUM` 為什麼救不了這個資料庫

`VACUUM` 的工作原理是：走訪所有頁面，把「已刪除但仍被佔用」的空洞擠壓掉，產生一份緊湊的新檔案。因此：

- `freelist_count = 0` → 沒有任何空洞 → 新檔案不會比原檔案小 → **零收益**
- 只有先 `DELETE` 掉資料（`session` → cascade 刪 `event`/`part`/`message`），才會產生空洞，`VACUUM` 才有東西可以擠

這是很多人「以為執行了 VACUUM 就省空間」的常見誤解來源。用 `PRAGMA freelist_count` 可以在 0.1 秒內判斷有沒有戲唱。

---

_最後更新：2026-09-27_

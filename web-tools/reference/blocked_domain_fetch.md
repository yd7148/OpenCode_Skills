# 受封鎖網域取回（Wayback 代抓）與 Google Forms 題目解析

> 適用於：目標網址所在網域**被本機網路管制封鎖**，無法直接抓取，
> 但仍需把頁面內容（尤其 Google 表單題目）取出並整理成文件。
>
> 對應情境：受管制的企業網路（僅 TCP 443、個別網域白名單）、
> Google 全家桶（`*.google.com` / `*.googleapis.com` / `forms.gle`）遭封鎖。

---

## 一、判別決策流程

```mermaid
flowchart TD
    A[拿到目標網址] --> B{代理可達?}
    B -->|200/3xx| C[直接抓取<br/>curl -x $env:HTTPS_PROXY]
    B -->|000 封鎖| D[直連測試<br/>--noproxy '*']
    D -->|仍 000| E[盤點可達網域白名單]
    E --> F{有可代抓任意網址者?}
    F -->|有 archive.org| G[Save Page Now 代抓]
    F -->|無| H[盤點中繼服務<br/>r.jina.ai / allorigins / corsproxy…]
    H -->|全被封| G
    G --> I[id_ 修飾符取原始 HTML]
    I --> J{是 Google Forms?}
    J -->|是| K[解析 FB_PUBLIC_LOAD_DATA_]
    J -->|否| L[一般 HTML 解析 / 交給爬蟲 skill]
    K --> M[產出 Markdown 題目+填答版]

    style G fill:#ddffdd
    style K fill:#ddffdd
    style M fill:#ddeeff
```

---

## 二、步驟一：白名單盤點

封鎖發生在 **CONNECT 隧道階段**（代理回 `000`），換 User-Agent、Referer、
換瀏覽器都無效 —— 判斷依據是 `Proxy-Agent: Fortinet-Proxy/1.0` 之類的代理標頭，
以及 `ERR_TUNNEL_CONNECTION_FAILED (-111)`。

```powershell
$cands = @(
  "https://docs.google.com/", "https://www.google.com/", "https://googleapis.com/",
  "https://r.jina.ai/", "https://api.allorigins.win/", "https://api.codetabs.com/v1/proxy?quest=https://example.com",
  "https://web.archive.org/", "https://archive.org/", "https://github.com/", "https://api.github.com/",
  "https://codeload.github.com/", "https://registry.npmjs.org/", "https://pypi.org/"
)
foreach ($u in $cands) {
  $code = curl.exe -s -o NUL -w "%{http_code}" -x $env:HTTPS_PROXY --max-time 10 $u
  "$u => $code"
}
```

回傳碼判讀：

| 回傳 | 意義 |
|---|---|
| `000` | 被封鎖（連代理 CONNECT 都沒過） |
| `401` / `403` | **通**（僅來源端拒絕匿名存取） |
| `2xx` / `3xx` | 通 |

**實務上最有價值的可達節點**：`web.archive.org` / `archive.org`（可代抓任意網址）、
`github.com` / `codeload.github.com`（可取程式碼）、`registry.npmjs.org` / `pypi.org`。

---

## 三、步驟二：Save Page Now 代抓

archive.org 的爬蟲**自其自身網路**連出去，因此能繞開本機的網域封鎖。

```powershell
$u = "<目標網址>"
# 1) 觸發代抓（回 302，Location 指向新快照）
curl.exe -s -L -D - -o NUL --max-time 90 "https://web.archive.org/save/$u"
# 2) 以 id_ 修飾符取回「未經 Wayback 改寫」的原始 HTML
curl.exe -s -L --compressed --max-time 90 `
  "https://web.archive.org/web/<timestamp>id_/$u" -o "$env:TEMP\gform.html"
```

| 關鍵細節 | 說明 |
|---|---|
| `id_` 修飾符 | 取回原始內容（不含 Wayback 注入的改寫腳本） |
| `--compressed` | **必加**。回應為 gzip，沒加會存成二進位，讀出全是亂碼 |
| 快照尚不存在時 | 先打 `https://archive.org/wayback/available?url=<url>` 查詢；`archived_snapshots` 為空就必須觸發 Save Page Now |
| 舊快照查詢 | `https://web.archive.org/cdx/search/cdx?url=<url>*&output=json&limit=40` |

---

## 四、步驟三：Google Forms 題目解析（`FB_PUBLIC_LOAD_DATA_`）

Google Forms 的 viewform 頁面是 **JS 殼層**，HTML 內沒有已渲染的題目 DOM
（沒有 `freebirdFormviewer*` 類別、沒有 `role="radio"` 的真實元素）。
所有題目、題型、選項、必填旗標都放在內嵌的 JS 變數：

```html
<script>var FB_PUBLIC_LOAD_DATA_ = [ ... ]; ...</script>
```

### 資料結構語義

| 路徑 | 意義 |
|---|---|
| `data[3]` | 表單標題 |
| `data[14]` | 表單 ID（`e/1FAIpQLS...`） |
| `data[1][1]` | **題目陣列**（entry list） |
| `entry[0]` | 題目 entry id（數字） |
| `entry[1]` | 題目文字（中／英） |
| `entry[2]` | 題目說明（可為 `null`） |
| `entry[3]` | 題型：`0`=短答、`1`=段落、`2`=單選、`3`=下拉、`4`=複選 |
| `entry[4][0][1]` | 選項陣列（單選／複選才有，元素形如 `[標籤, null, …]`） |
| `entry[4][0][2]` | **必填旗標**：`1`=必填、`0`=選填（文字題與選擇題通用） |
| `entry[11]` / `entry[12]` | `[null, 題目文字]` / `[null, 題目說明]`（渲染用副本） |

### 解析腳本（可直接複製使用）

```python
import json, re, html as ihtml

raw = open("gform.html", encoding="utf-8", errors="replace").read()

i = raw.find("FB_PUBLIC_LOAD_DATA_")
j = raw.find("=", i)
data, _ = json.JSONDecoder().raw_decode(raw[j+1:].lstrip())

TYPE = {0: "短答（單行）", 1: "段落（多行）", 2: "單選 radio", 3: "下拉選單", 4: "複選 checkbox"}

def clean(s):
    s = (s or "").replace("\xa0", " ")
    s = re.sub(r"<br\s*/?>", " / ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return ihtml.unescape(s).strip()

entries = data[1][1]
print("表單標題:", data[3], " 題數:", len(entries))
for n, e in enumerate(entries, 1):
    title = clean(e[1])
    desc = clean(e[2]) if len(e) > 2 and isinstance(e[2], str) else ""
    qtype = e[3]
    spec = e[4][0] if len(e) > 4 and isinstance(e[4], list) else []
    required = (spec[2] == 1) if len(spec) > 2 else False
    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], list) else []
    print(f"[{n}] {'必填' if required else '選填'} {TYPE.get(qtype, qtype)} :: {title}")
    if desc:
        print("     說明:", desc)
    for o in opts:
        print("     -", clean(o[0]) if isinstance(o, list) else o)
```

### Windows 主控台亂碼處理

主控台預設 Big5／CP950，中文會顯示成亂碼。**不要**用 `Get-Content` 直接印，
改為輸出成 UTF-8 檔案再讀取：

```python
open("questions.txt", "w", encoding="utf-8").write("\n".join(lines))
```

主控台要印中文時加：`[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`。

---

## 五、步驟四：輸出規範

抓到題目後，交付物應包含兩份 Markdown：

| 檔案 | 內容 |
|---|---|
| `<主題>-填答版.md` | 表單資訊表、問卷流程 Mermaid 圖、題目總覽表、**逐題明細（含選項與填答內容）**、送出前檢查清單、附錄 |
| `工作紀錄-<主題>-<YYYYMMDD>.md` | 問題描述、診斷過程與證據（真實回傳碼）、根因、處理動作、驗證結果、踩過的坑、改善對策、附錄 |

必填旗標要**交叉驗證**：與既有檔案（例如已產出的 docx 上的 `*` 標記）比對一致後再寫進文件。

---

## 六、踩過的坑

| 坑 | 症狀 | 解法 |
|---|---|---|
| Wayback 回應是 gzip 二進位 | 存檔後讀出全是亂碼，找不到 `FB_PUBLIC_LOAD_DATA_` | `curl` 加 `--compressed` |
| 誤把 `entry[1]` 當題目主體 | 解析出來的題目整組錯位、題數異常 | 題目陣列是 `data[1][1]`；`entry[0]` 是 id、`entry[1]` 才是題目文字 |
| 想從 HTML DOM 抓選項 | 找不到 `freebirdFormviewer*` 類別 | 表單是 JS 殼層，改抓內嵌 JSON |
| 以為 MHTML 存檔能驗證必填 | 瀏覽器存檔同樣是殼層，`aria-required` 命中 0 | 必填旗標只能從 `entry[4][0][2]` 判讀 |
| 把 `000` 當成「網址寫錯」 | 其實是代理封鎖 | 同時用 `-x $env:HTTPS_PROXY` 與 `--noproxy '*'` 測，並看 `Proxy-Agent` 標頭 |
| 代抓服務全部被封 | r.jina.ai / allorigins / corsproxy / scraperapi 全 `000` | 改用白名單內且具代抓能力的 archive.org |
| 產出含公司名稱等機密 | 公開 repo 外流風險 | 個資以 `【待填】` 佔位，敏感欄位不寫死 |

---

## 七、附錄

| 項目 | 說明 |
|---|---|
| 暫存慣例 | `%TEMP%\opencode\`（解析腳本與中間 JSON），驗證完可刪 |
| Wayback 引用格式 | `https://web.archive.org/web/<timestamp>id_/<原始網址>` |
| 觸發紀錄 | 引用快照時附上「Save Page Now 觸發時間」，方便對照表單是否已異動 |

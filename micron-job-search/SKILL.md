---
name: micron-job-search
description: Use when the user wants to search, filter, categorize, or analyze Micron Technology job openings (careers.micron.com / Eightfold), especially for a specific location such as Taichung 台中, F16/F18, or Taiwan fabs; when they ask for a job-posting analysis report with Markdown tables and Mermaid charts; when they ask for Req IDs, direct apply links, or JD requirement extraction; or when they ask about Micron resume format, ATS rules, or how to apply. Covers rate-limit-safe scraping of the Eightfold career site, JD requirement parsing, resume-format rules from micron.com, and Markdown/PDF report generation.
license: MIT
---

# Micron Job Search — 台中職缺抓取與分析

## 路徑須知

本 skill 內的絕對路徑來自**撰寫時的機器**，在其他機器上不一定存在。執行前請：

- **skills 目錄**以 `~/.config/opencode/skills/` 為準（PowerShell 用 `Join-Path $env:USERPROFILE ".config\opencode\skills"` 推導），不要假設是 `<PROJECT_ROOT_A>\.opencode\skills\` 或任何特定磁碟機。
- **專案／輸出／暫存路徑**先確認存在；找不到就問使用者實際路徑，不要自行猜測或建立。
- 本 skill（包含 `references/`）出現的 `<PROJECT_ROOT_C>` 等前綴屬**操作紀錄範例**，不是可依賴的事實。

Micron 職缺查詢、分類、条件解析、履歷格式研究與報告產出的一條龍流程。

## 關鍵前提：網站架構

| 項目 | 事實 |
|---|---|
| 職缺站台 | `https://careers.micron.com/careers`（AEM + **Eightfold AI** 前端） |
| 另一入口 | `https://micron.wd1.myworkdayjobs.com/en-US/External`（Workday，結果較少） |
| 列表選擇器 | `[data-test-id="job-listing"]` |
| 標題選擇器 | `div[class*="title-"]` |
| 地點選擇器 | `div[class*="fieldValue-"]` |
| 職缺連結 | `a[href*="/careers/job/"]` → `https://careers.micron.com/careers/job/<id>` |
| Req ID | 職缺頁內文出現的 `JR\d{6}`（例：`JR112135`） |
| 機器人防護 | **有人類驗證牆**。短時間大量請求會觸發，頁面只剩語言選擇清單（約 200 字元） |

## 三個不可省略的教訓

1. **Webfetch 抓不到職缺清單**。職缺列表是 JS 動態渲染，原始 HTML 只有 JSON 設定殘留，`<title>` 只會給出「目前開啟的第一筆職缺」。
2. **不要直接呼叫 `/api/apply/v2/jobs`**。未登入時回傳 `{"message":"Not authorized for PCSX"}`，從 PowerShell/curl 呼叫回 403。
3. **必須用 Playwright headless Chromium 渲染**，`wait_until="domcontentloaded"` 後等 3–8 秒再取 `document.body.innerText` / `evaluate`。

## 執行流程

### Step 1 — 抓取職缺列表

```bash
python <skill>/scripts/fetch_list.py --location "Taichung City, Taiwan" --out micron_tc.json
```

原理：以 `?start=N` 分頁參數逐頁 goto（每頁 20 筆），每頁間隔數秒，只保留 `fields` 中含目標地點者。以 URL 去重。

**務必傳入真實 UA**（`Chrome/140.0.0.0`）並設定 `locale="en-US"`，可大幅降低被擋機率。

### Step 2 — 抓取 Job Description 內文

```bash
python <skill>/scripts/fetch_jd.py --list micron_tc.json --out micron_texts.json
```

**這步最關鍵，務必遵守：**

| 參數 | 值 | 原因 |
|---|---|---|
| 並行頁數 | **1** | 5 頁並行會立刻觸發驗證牆 |
| 每頁間隔 | **2.5–4.5 秒**（隨機） | 過快直接被擋 |
| UA | 固定真實 Chrome UA | 降低辨識率 |
| 失敗重試 | 最多 4 次，每次冷卻 20/40/60 秒 | 驗證牆通常是分鐘級冷卻 |
| 健康檢查 | `len(innerText) < 2000` 視為被擋 | 被擋時正文約 200 字元 |
| 落地存檔 | 每 20 筆寫一次 JSON | 中斷可續跑 |
| 續跑 | 讀入既有 JSON，只補抓缺少的 URL | 分批作業必備 |

完整 213 筆單執行緒約需 15–20 分鐘。**被擋時不要硬衝，先 `Start-Sleep 300` 冷卻。**

### Step 3 — 解析條件

```bash
python <skill>/scripts/parse_jd.py --texts micron_texts.json --list micron_tc.json --out micron_final.json
```

職缺 JD 結構不統一，必須多軌取qualifications：

- 標題常見：`Qualifications` / `Minimum Qualifications` / `Basic Qualifications` / `Required Qualifications` / `Requirements` / `Education`
- **約 60% 的職缺根本沒有「Qualifications」段落**，條件散落在 `Responsibilities` 內或直接寫在導言。因此必須 fallback 到 Responsibilities。
- 抓不到標題時改用「最長連續短行區塊」估計
- 學歷判定：`Ph.D/doctorate` → PhD；`M.S/Master` → MS；`B.S/Bachelor` → BS；皆無 → `—`
- 經驗年數：`re.findall(r"(\d+)\+?\s*years", txt, re.I)`
- 發布時間：`Posted\s+(\d+\s+\w+\s+ago)`

### Step 4 — 分類與產報告

```bash
python <skill>/scripts/build_report.py --final micron_final.json \
  --md "E:\path\Micron_台中職缺分析報告.md"
```

分類規則（職稱關鍵字，順序敏感）見 `build_report.py` 的 `cat()`。**先排除**實習/校園/招募與技術員/操作員，再依序比對管理師 → AI/資料 → 供應鏈 → 品質 → 廠務 → 工程師。

報告格式：統計表 + Mermaid（`pie` 圓餅、`xychart-beta` 長條、`flowchart` 生態系）+ 分節完整清單（附 Req ID 與投遞連結）+ 條件摘要 + 關鍵字頻率表。

### Step 5 — 轉 PDF（可選）

複製 `~/.config/opencode/skills/md-to-pdf/make_md_pdf.py`，只改 `SRC` / `OUT` 兩行，用有 Pillow 的 python 執行。

> Mermaid 程式碼區塊在 PDF 中會以等寬文字呈現（不會算繪成圖），這是預期行為；要看圖請開 .md。

## Micron 履歷格式（官方權威來源）

來源：`https://www.micron.com/about/careers/mail-fax-help`

### 官方明訂

| 項目 | 規範 |
|---|---|
| 投遞方式 | **只接受線上投遞**，郵寄/傳真不受理 |
| 姓名 | 必須第一行 |
| 聯絡資訊 | 地址、電話、E-mail 緊接姓名下一行 |
| 頂部裝飾 | 禁止 Logo 或特殊圖像 |
| 字級 | 10–14 pt |
| 字型 | Sans-serif 最佳（Helvetica / Arial）；禁裝飾字型 |
| 斜體/底線 | 禁止；可用粗體與全大寫 |
| 表格/框線 | 避免水平線、垂直線、表格、多欄 |

### ATS（Workday + Eightfold AI）

- 格式 **.docx 或純文字 PDF**；**絕對不可用掃描影像 PDF**
- 標準段落標題：`Work Experience` / `Education` / `Skills` / `Certifications`
- 禁用：多欄、頁首頁尾承載關鍵資訊、表格、圖片式技能表
- 驗證法：複製貼到純文字編輯器，閱讀順序正常即代表可解析
- **務必填完 Workday profile 所有選填欄位**（證照、語言、退伍役別），recruiter 篩選會排除未完成者
- 上傳後**檢查自動回填欄位**是否正確（日期、職稱錯置會直接扣分）
- 鏡射職缺原文關鍵字（HBM / DFT / ATE / MATLAB / Python / SPC / DOE …）

### AI 使用聲明（每份 JD 都有）

> Candidates are encouraged to use AI tools to enhance your resume... Misuse of AI to fabricate or misrepresent qualifications will result in immediate disqualification.

允許用 AI 協助，但內容必須真實。

### 官方求職專線

`1-800-336-8918` 或 `208-368-4748`（無障礙协助）

## 投遞入口

| 用途 | 網址 |
|---|---|
| 主要職缺頁 | `https://careers.micron.com/careers` |
| 單一職缺 | `https://careers.micron.com/careers/job/<id>` |
| 候選人中心 | `https://careers.micron.com/careers/dashboard` |
| Workday | `https://micron.wd1.myworkdayjobs.com/en-US/External` |
| 不使用 AI 招募軟體 | 履歷寄至 `TA_EMEA@<CORP_DOMAIN>`，並註明 Req ID |

## 台中廠背景（有助於解讀職缺代號）

| 代號 | 意義 |
|---|---|
| `F16` | Fab 16，3D NAND |
| `HBM` | High Bandwidth Memory，當前最熱門成長動能 |
| `MTB` | Micron Taiwan Building，新廠（職稱帶此代號者多為新建置期人力） |
| `FY28 NCG` | Fiscal 2028 New Capacity Generation，新世代產能計畫 |
| `PI / PIE / CPIE` | Process Integration，製程整合 |
| `NDA / RDA / WEA` | 記憶體製程團隊代號 |
| `PDE / MTB / APTD` | 產品工程師線 |
| `TCP / ATE / OMT` | 測試與組裝線 |

## 報告輸出慣例

- 繁體中文
- 檔名 `Micron_台中職缺分析報告.md` / `Micron_台中職缺_目標職類分析報告.md`
- 存放於 `<PROJECT_ROOT_C>\2026-09-CV\`
- 表格欄位：職缺標題、Req ID、職級、學歷、經驗年數、發布時間、投遞連結

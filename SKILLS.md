# OpenCode Skills 說明文件

本收藏庫目前收錄 **39 個 skills**。每個 skill 都是一個資料夾，內含 `SKILL.md`
（YAML frontmatter 的 `name` + `description` 決定觸發時機）與選用的 `references/`、`scripts/`。

> **同步**：本機 `~/.config/opencode/skills/` ↔ 本 repo，由 `github-skill-sync` skill 負責。
> **整併**：功能重疊的 skill 已合併為單一 skill，子功能說明置於該 skill 的 `references/`。
> **來源**：各 skill 的權威說明是該資料夾內的 `SKILL.md`。本文件是摘要與索引，
> 若與 `SKILL.md` 不一致，**以 `SKILL.md` 為準**。

---

## ⚠️ 路徑可攜性規範（重要）

本收藏庫的 skill 是在**多台機器**上撰寫與使用的（先後用到 `<USER_1>`、`<USER_2>`、`<USER_3>`
等使用者帳號，以及 `<PROJECT_ROOT_A>`、`<PROJECT_ROOT_B>`、`<PROJECT_ROOT_C>` 等磁碟機根目錄）。
因此 skill 內出現的絕對路徑**只在他們被記錄的那台機器上有效**。

執行任何 skill 之前：

| 項目 | 做法 |
|---|---|
| **skills 目錄** | 一律視為 `~/.config/opencode/skills/`。PowerShell 用 `Join-Path $env:USERPROFILE ".config\opencode\skills"` 推導，**不要**假設是 `<PROJECT_ROOT_A>\.opencode\skills\` 或任何特定磁碟機 |
| **專案／輸出／暫存路徑** | 先確認存在再用；找不到就問使用者實際路徑，**不要**自行猜測或建立資料夾 |
| **文件中的絕對路徑** | 視為**操作紀錄範例**，不是可依賴的事實 |
| **工具預設位置** | 諸如 ffmpeg、ExifTool、Python、COMSOL 的路徑，先用 `Get-Command`／`where.exe` 實際探测 |

含他機路徑、已加上「## 路徑須知」段落的 skill：
`cv-job-application`、`dwg-to-dxf`、`exam-report`、`md-to-pdf`、
`micron-job-search`、`on24-video-download`、`opencode-session-auto-name`、`pdf-reader`、
`takeout-exif-merge`、`video-analysis`、`yt-batch-download`。

另有兩個 skill 自行處理了此問題：`github-skill-sync`（全面改為執行時解析路徑）、
`yd7148-portfolio-deploy`（標註需先確認專案根目錄）。

---

## 分類總覽

### 全部 skills 一覽

| # | Skill | 一句話說明 |
|---:|---|---|
| 1 | [`dwg-to-dxf`](#1-dwg-to-dxf) | Convert AutoCAD DWG files to DXF format using ODA File Converter, then perform detailed geometric and metadat… |
| 2 | [`sd-webui-vae-fix`](#2-sd-webui-vae-fix) | 修復 AUTOMATIC1111 Stable Diffusion WebUI（A1111 / sd.webui）「無法切換」檢查點或 VAE 的錯誤（sd_model_checkpoint / sd_vae 選擇失敗… |
| 3 | [`docx-edit`](#3-docx-edit) | Use when the user asks to read, edit, convert, extract from, or generate Word .docx files (新增/修改/取代 Word 內容、表… |
| 4 | [`image-to-pdf`](#4-image-to-pdf) | 將一個資料夾內的圖片（PNG/JPG 等）合併成單一 PDF，每一頁一張圖片、依檔名順序排列，使用 Pillow 離線產生。Use when asked to "圖片轉 PDF", "圖片合併成 PDF", "每一頁一… |
| 5 | [`line-group-export-analysis`](#5-line-group-export-analysis) | 匯入並分析 LINE 群組聊天記錄（手機「匯出聊天記錄」產生的 txt/zip，或以 Browser Control 從 LINE Web 分頁逐段捲動擷取），產出每人發文量與頻率、活躍時段、回覆互動網路、訊息長度分布… |
| 6 | [`md-to-pdf`](#6-md-to-pdf) | 將繁體中文 Markdown 說明檔渲染成排版精美的 A4 多頁 PDF（標題、表格、代碼區塊、引言、頁碼），使用 Pillow + 微軟正黑體離線產生，不需網路。Use when asked to "寫一個MARKD… |
| 7 | [`meeting-transcript-summary`](#7-meeting-transcript-summary) | 將一場會議的「原始時間戳逐字稿」（*_timestamp.txt，語音辨識輸出）彙總成詳盡繁體中文主管會議紀錄摘要（含各主管問題、部屬答覆、目標與代辦事項），存成 <BASE>_會議彙總.md。Use when ask… |
| 8 | [`news-weekly-docx-move`](#8-news-weekly-docx-move) | Use when the user asks to bulk-move, copy, collect, or sync the weekly news review .docx files (個人週報 新聞(OK).d… |
| 9 | [`pdf-reader`](#9-pdf-reader) | 讀取 PDF 檔案的內容並輸出成 Markdown 摘要報告。文字型 PDF 用 PyMuPDF 直接抽取（含中文）；掃描/圖片型 PDF 自動渲染成 PNG 並以 RapidOCR 辨識；輸出以 opencc 轉為繁… |
| 10 | [`pptx`](#10-pptx) | Use when generating or manipulating PowerPoint presentations programmatically. |
| 11 | [`xlsx`](#11-xlsx) | Use when creating, reading, or manipulating Excel workbooks programmatically with formulas, charts, and forma… |
| 12 | [`zh-text-polish`](#12-zh-text-polish) | 繁體中文錯字校對與文句潤飾（會議紀錄、公文、技術報告），輸出錯字對照表＋修訂全文＋Markdown表格與Mermaid流程圖。Use when asked to "確認錯字", "文句潤飾", "會議紀錄校對", "公… |
| 13 | [`exam-report`](#13-exam-report) | Use when the user needs to process 國營事業 / 台電 / 中油 / 中水 / 台糖 recruitment exam PDFs. |
| 14 | [`on24-video-download`](#14-on24-video-download) | 下載 ON24 線上研討會活動（event.on24.com）的影片、投影片與字幕，並從下載的主影片自動提取「投影片 PDF / 投影片影片 / 時間軸摘要」。涵蓋公開媒體組態 API、download/CDN URL… |
| 15 | [`takeout-exif-merge`](#15-takeout-exif-merge) | Use when the user asks to merge Google Photos Takeout supplemental-metadata.json sidecar files into the same-… |
| 16 | [`tts`](#16-tts) | 使用 Microsoft Edge 的 edge-tts 將文字轉成高品質語音（Text-to-Speech），支援繁體中文、簡體中文、粵語與多國語言與多種聲音。可將文字轉成 mp3 語音檔，並可調整速率、音量、音調，… |
| 17 | [`twii-excel-fill`](#17-twii-excel-fill) | Use when the user wants to fill in 台股加權指數（發行量加權股價指數）每日漲跌點數 into an Excel 活頁簿（例如「2026-10-02-股價+加密+藥.xlsx」的分頁「1… |
| 18 | [`video-analysis`](#18-video-analysis) | Use when the user wants to analyse or process 影片 (course videos, YouTube live class sessions, screen recordin… |
| 19 | [`yt-batch-download`](#19-yt-batch-download) | 批次下載 YouTube 影片（1080p 最高畫質），支援自訂檔名、cookies 匯入、SSL 修復、JS runtime 設定。Use when asked to "下載YouTube影片", "批次下載YT",… |
| 20 | [`yt-upload`](#20-yt-upload) | 透過 Playwright 操作 YouTube Studio，將本機影片上傳並公開發布為 YouTube 影片。支援填寫詳細的標題、說明、標籤、主題標籤，設定目標觀眾（非兒童專屬）、瀏覽權限（公開/不公開/私人），並… |
| 21 | [`browser-control`](#21-browser-control) | Drive the user's existing Chromium-family browser with deterministic Playwright. |
| 22 | [`open-computer-use`](#22-open-computer-use) | Platform-neutral guidance for using Open Computer Use, the open-source Computer Use MCP server and CLI for ma… |
| 23 | [`opencode-browser`](#23-opencode-browser) | 用 OpenCode 外掛 `@different-ai/opencode-browser`（OpenCode Browser）控制使用者「既有」的 Chrome／Edge／Chromium 視窗，沿用同一個 prof… |
| 24 | [`web-tools`](#24-web-tools) | Use when the user needs to fetch web pages or automate a browser. |
| 25 | [`cv-job-application`](#25-cv-job-application) | Use when 投遞或填寫 中華電信/台積電 線上履歷、要操作 rmis.cht.com.tw 報名表（自動填表、附件上傳、狀態檢核）、要沿用已保存的 Chrome 登入資訊（.pw-profile）登入、需要把台積… |
| 26 | [`micron-job-search`](#26-micron-job-search) | Use when the user wants to search, filter, categorize, or analyze Micron Technology job openings (careers.mic… |
| 27 | [`resume-cloudflare-maintenance`](#27-resume-cloudflare-maintenance) | 維護劉士禎的 Resume 01 個人履歷網站與 Cloudflare Workers 靜態部署；用於本專案更新中英內容、保留舊版、建立發布副本、調整 workers.dev 網址或還原。不是通用網站建置 Skill。 |
| 28 | [`taobao-cost`](#28-taobao-cost) | Use when the user works with 淘obao (Taobao) exported order data or 淘寶費用計算明細 spreadsheets. |
| 29 | [`yd7148-portfolio-deploy`](#29-yd7148-portfolio-deploy) | Use when 維護／部署／改網址／改路由／處理個資 for 劉士禎的三個個人網站（Astro 7 + Tailwind v4 + GitHub Pages + Actions 自動部署）—— repo `cv1`（… |
| 30 | [`astro-dev`](#30-astro-dev) | \|- Build and debug Astro sites: content collections, islands architecture, rendering modes, and image/SEO bas… |
| 31 | [`cloudflare-platform`](#31-cloudflare-platform) | Use when building or deploying on Cloudflare's core platform — Workers, Pages, KV, R2, D1, AI, or networking… |
| 32 | [`github-skill-sync`](#32-github-skill-sync) | 同步本機 OpenCode skills（`~/.config/opencode/skills/`）與 GitHub 上的 `yd7148/OpenCode_skill` 收藏庫。本 skill 同時管理**下載（Gi… |
| 33 | [`mac-disk-cleanup`](#33-mac-disk-cleanup) | 掃描與清理 macOS 磁碟空間：定位大目錄（家目錄、Applications、/Library/Application Support、CloudStorage、/private/var）、辨識可安全刪除的快取與孤兒… |
| 34 | [`network-port-check`](#34-network-port-check) | 檢查本機對外網路連線狀態（Windows PowerShell 與 macOS bash 雙版本）：哪些 TCP port 通、哪些被防火牆擋、遠端服務（RDP/SSH/VNC）能否接通、有哪些網站被擋、TLS 是否被… |
| 35 | [`opencode-session-auto-name`](#35-opencode-session-auto-name) | 讓 opencode 的 session 標題自動以「第一次 prompt 的總結」命名（或進行中 todo）。使用本 skill 內建的 OpenCode V2 plugin（0 Token、純規則式、與模型無關、零… |
| 36 | [`opencode-usage`](#36-opencode-usage) | Monitor and report OpenCode usage, quota, and local resource consumption. |
| 37 | [`py-binary-deps`](#37-py-binary-deps) | Use when a CLI tool or native binary must be installed on this machine — ffmpeg, yt-dlp, ffprobe, node, uv, r… |
| 38 | [`comfyui-qwen-image-edit`](#38-comfyui-qwen-image-edit) | 用 ComfyUI + Qwen-Image-2.1 做圖像編輯（改圖／換裝／服裝轉移／多圖參考）與文生圖，產出可直接拖入 ComfyUI 的工作流 JSON，並用 /prompt API 批次執行。涵蓋兩個會「不報錯… |
| 39 | [`mate-engine`](#39-mate-engine) | Mate Engine / Mate Engine X（免費輕量桌面寵物、Desktop Mate 替代品）的下載、安裝執行，以及動作數量擴充（把 Assembly-CSharp.dll 的 totalIdleAnim… |

## Skill 詳細說明

## 1. dwg-to-dxf
[dwg-to-dxf/SKILL.md](dwg-to-dxf/SKILL.md)

# dwg-to-dxf — DWG 轉 DXF 與詳細解析

Convert an AutoCAD `.dwg` file to `.dxf` format using ODA File Converter, then perform
comprehensive geometric and metadata analysis using Python `ezdxf` library. Produces a
detailed Traditional Chinese markdown documentation report.

## When to use
- User says 轉換 DWG / DWG 轉 DXF / 分析 DWG 檔案 / dwg to dxf conversion / DWG 幾何分析, or hands you a `.dwg` file to analyze.
- Also use when the user asks about layers, dimensions, geometry, blocks, or any content in an AutoCAD drawing file.

---

## 2. sd-webui-vae-fix
[sd-webui-vae-fix/SKILL.md](sd-webui-vae-fix/SKILL.md)

# sd-webui-vae-fix — A1111 檢查點／VAE 切換失敗修復

修 AUTOMATIC1111 Stable Diffusion WebUI（下方稱 A1111）中「切換檢查點或 VAE 失敗」的問題。

## 觸發情境（何時使用此 skill）

---

## 3. docx-edit
詳見 [docx-edit/SKILL.md](docx-edit/SKILL.md)。

Use when the user asks to read, edit, convert, extract from, or generate Word .docx files (新增/修改/取代 Word 內容、表…

---

## 4. image-to-pdf
[image-to-pdf/SKILL.md](image-to-pdf/SKILL.md)

# image-to-pdf — 圖片 → 單一 PDF（每頁一張，依檔名排序）

把一個資料夾內的圖片（`.png` / `.jpg` 等）合併成**單一 PDF**：
**每一頁一張圖片、依照檔案名稱順序排列**。用 Pillow 離線產生，不需網路。

## When to use

---

## 5. line-group-export-analysis
詳見 [line-group-export-analysis/SKILL.md](line-group-export-analysis/SKILL.md)。

匯入並分析 LINE 群組聊天記錄（手機「匯出聊天記錄」產生的 txt/zip，或以 Browser Control 從 LINE Web 分頁逐段捲動擷取），產出每人發文量與頻率、活躍時段、回覆互動網路、訊息長度分布…

---

## 6. md-to-pdf
[md-to-pdf/SKILL.md](md-to-pdf/SKILL.md)

# md-to-pdf — 繁中 Markdown → A4 PDF（離線 Pillow 渲染）

把一份繁體中文 `.md` 說明檔同時交付為 **Markdown + 排版 PDF** 兩個檔案。
PDF 由 Pillow 直接繪製文字（非圖片截圖、非 reportlab），中文以微軟正黑體呈現，
支援 H1/H2/H3 標題、表格（自動欄寬＋斑馬紋）、圍欄代碼區塊、引言區塊、
有序／無序清單、分隔線與頁尾頁碼。

## When to use

---

## 7. meeting-transcript-summary
[meeting-transcript-summary/SKILL.md](meeting-transcript-summary/SKILL.md)

# meeting-transcript-summary — 原始時間戳會議逐字稿 → 詳盡繁中會議彙總

把語音辨識（Whisper/faster-whisper 等）產出的「每行一段、帶時間戳」逐字稿
（如 `2026-08-31 08-25-42_timestamp.txt`）彙總成 **詳盡繁體中文主管會議紀錄**，
交付為 `<BASE>_會議彙總.md`（同一專案資料夾）。輸出須「條列各主管問題與部屬答覆」
並「列出指示／須完成目標與代辦事項」。

## When to use
- User 給你一個 `*_timestamp.txt`（或任一語音辨識逐字稿），要求「彙總會議紀錄」
- 要求「詳細彙總、條列各主管問題與部屬答覆、指示須完成目標與代辦事項」
- 需要把長達數小時的半導體／製造業／任何專業會議逐字稿，濃縮成可讀的會議紀錄

---

## 8. news-weekly-docx-move
詳見 [news-weekly-docx-move/SKILL.md](news-weekly-docx-move/SKILL.md)。

Use when the user asks to bulk-move, copy, collect, or sync the weekly news review .docx files (個人週報 新聞(OK).d…

---

## 9. pdf-reader
[pdf-reader/SKILL.md](pdf-reader/SKILL.md)

# pdf-reader — 讀取 PDF 內容並輸出 Markdown 摘要

讀取指定的 `.pdf` 檔案，萃取每頁文字（含中文），對掃描/圖片型頁面自動做 OCR，
並把整份內容輸出成一份 Markdown 摘要報告。

## When to use

---

## 10. pptx
詳見 [pptx/SKILL.md](pptx/SKILL.md)。

Use when generating or manipulating PowerPoint presentations programmatically.

---

## 11. xlsx
詳見 [xlsx/SKILL.md](xlsx/SKILL.md)。

Use when creating, reading, or manipulating Excel workbooks programmatically with formulas, charts, and forma…

---

## 12. zh-text-polish
詳見 [zh-text-polish/SKILL.md](zh-text-polish/SKILL.md)。

繁體中文錯字校對與文句潤飾（會議紀錄、公文、技術報告），輸出錯字對照表＋修訂全文＋Markdown表格與Mermaid流程圖。Use when asked to "確認錯字", "文句潤飾", "會議紀錄校對", "公…

---

## 13. exam-report
[exam-report/SKILL.md](exam-report/SKILL.md)

# Taipower Exam Report

End-to-end workflow: OCR-extracted exam questions → (for circuit diagrams) Qwen2.5-VL-7B component extraction → SP topologies back-inferred from values + official answer → ngspice/PySpice simulation → verdict (PASS/REVIEW/SIM-ERR) → merge with per-question authoritative content into a complete detailed-answer markdown report.

## Year Pair (113 / 114 電機)

子功能參考文件：

- [`reference/pdf-exam-extractor.md`](exam-report/reference/pdf-exam-extractor.md)
- [`reference/taipower-exam-solver.md`](exam-report/reference/taipower-exam-solver.md)

---

## 14. on24-video-download
[on24-video-download/SKILL.md](on24-video-download/SKILL.md)

# ON24 活動影片下載與投影片提取

將 ON24 研討會（例如 Microsoft Agent-a-thon / Frontier Transformation Week 的 simulive 活動）的
影片、投影片、字幕全部抓到本機，並可從主影片自動抽出「投影片 PDF / 投影片影片 / 時間軸摘要」。

## WHEN TO USE

---

## 15. takeout-exif-merge
[takeout-exif-merge/SKILL.md](takeout-exif-merge/SKILL.md)

# Google Photos Takeout EXIF Merge

Merge `*.jpg.supplemental-metadata.json` (and `(N)` counter variants) sidecar metadata into the media files in place, using ExifTool. Proven pipeline: `scripts/merge_exif.py` (Python 3 + ExifTool via winget/`OliverBetz.ExifTool`).

## Key Facts

---

## 16. tts
[tts/SKILL.md](tts/SKILL.md)

# tts — 文字轉語音（edge-tts）

將文字內容轉成語音檔案（.mp3），使用 **Microsoft Edge 的雲端神經語音**（edge-tts）。
不需本機模型，語音品質高，支援繁體中文（正體）等多語系。

## 適用時機
- 使用者要求「文字轉語音」、「TTS」、「產出語音檔」、「把這段文字變成聲音」
- 需要影片旁白 / voiceover 的語音音檔
- 需要朗讀文稿、電子報、字幕的語音版本

---

## 17. twii-excel-fill
詳見 [twii-excel-fill/SKILL.md](twii-excel-fill/SKILL.md)。

Use when the user wants to fill in 台股加權指數（發行量加權股價指數）每日漲跌點數 into an Excel 活頁簿（例如「2026-10-02-股價+加密+藥.xlsx」的分頁「1…

---

## 18. video-analysis
[video-analysis/SKILL.md](video-analysis/SKILL.md)

# video2text — 影片分析（畫面 OCR × 語音 Whisper → Markdown + PDF）

Analyze a recorded meeting / online conference video into two deliverables, placed in the
user's project folder (e.g. `<PROJECT_ROOT_A>\Projects\<project>\`):

1. A Traditional Chinese markdown report: 分析方法 / 影片概述 / 時間軸重點摘要（OCR×Whisper 比對表）/ 重點知識點解析 / 外部資料交叉比對 / 幻覺偵測 / 驗證 / 結論 / 附註.
2. A key-frame PDF (screenshots of representative slides with time + caption).

子功能參考文件：

- [`reference/v2t-report-summary.md`](video-analysis/reference/v2t-report-summary.md)
- [`reference/video-2x-speed.md`](video-analysis/reference/video-2x-speed.md)
- [`reference/video-class-pipeline.md`](video-analysis/reference/video-class-pipeline.md)

---

## 19. yt-batch-download
[yt-batch-download/SKILL.md](yt-batch-download/SKILL.md)

# yt-batch-download — YouTube 批次下載（1080p）

批次下載多支 YouTube 影片，1080p 最高畫質，自訂檔名，支援 livestream (`youtube.com/live/ID`) 與一般影片 (`youtube.com/watch?v=ID`)。

## When to use
- User asks 下載 YouTube 影片 / 批次下載 YT / download YouTube videos batch / 下載課程影片
- 需要從 GitHub README 或其他來源取得 URL 列表並批次下載
- 需要自訂輸出檔名（依日期、時段等）

---

## 20. yt-upload
[yt-upload/SKILL.md](yt-upload/SKILL.md)

# yt-upload — YouTube 影片上傳並公開發布

透過 Playwright 操作 YouTube Studio (`studio.youtube.com`)，將本機影片（.mp4）上傳、填寫詳細資訊、設定為公開並擷取發布連結。

## When to use
- User 要求把本機影片上傳到 YouTube 並公開給大家觀看
- 需要填寫影片標題、說明、標籤等詳細資訊
- 需要設定影片為「公開 / 不公開 / 私人」瀏覽權限
- 需要取得發布後的影片連結（`https://youtu.be/VIDEO_ID`）

---

## 21. browser-control
[browser-control/SKILL.md](browser-control/SKILL.md)

# Browser Control

Browser Control is a **driver**, not an agent. The calling agent decides what to
do; Browser Control runs deterministic Playwright code in the user's visible
browser.

Use one loop throughout: **inspect, act, verify**. Inspect the real page before
choosing locators, act through the narrowest stable control, then verify the
result through a URL or fresh page read. Never treat a successful click or human
acknowledgment as proof that the task succeeded.

---

## 22. open-computer-use
[open-computer-use/SKILL.md](open-computer-use/SKILL.md)

# Open Computer Use

## Overview

Open Computer Use exposes Computer Use as a local CLI and stdio MCP server. It is not Codex.app-specific; adapt the commands and MCP config to the agent runtime you are operating in.

---

## 23. opencode-browser
[opencode-browser/SKILL.md](opencode-browser/SKILL.md)

# OpenCode Browser

用 OpenCode 外掛 `@different-ai/opencode-browser` 控制使用者**既有**的 Chrome／Edge／Chromium
視窗，沿用同一個 profile、已登入狀態與既有分頁，不另開隔離環境、不重跑登入流程。

- **安裝**：`opencode plugin add @different-ai/opencode-browser@latest` ＋ `npx @different-ai/opencode-browser@latest install`（broker / native host / 登錄機碼）。
- **載入既有 profile**：Chrome 137+ 已移除 `--load-extension`，改用 CDP `Extensions.loadUnpacked`；
  擴充功能 ID 由 manifest 的 `key` 固定，無須手動查詢。
- **驅動**：24 支 `browser_*` 工具；跨多步驟工作需維持**單一 session**（分頁所有權 per-session、租約 300 秒）。
- **互動**：Polymer / YouTube 新版元件需送**真實滑鼠事件**（CDP `Input`），座標一律由 `getBoundingClientRect()` 取得。
- **實戰**：YouTube 播放清單重排（排序 chip ＋ 每列「移至頂端」反向搬移演算法）。

---

## 24. web-tools
[web-tools/SKILL.md](web-tools/SKILL.md)

# web-tools — 本機網頁工具環境

本 skill 說明本機已安裝的三個網頁相關工具環境與使用方式，供 agent 在需要爬蟲、瀏覽器自動化或**網域被封鎖**時引用對應的環境與路徑。

## 工具一：Crawl4AI（網頁爬蟲 → Markdown）

子功能參考文件：

- [`reference/blocked_domain_fetch.md`](web-tools/reference/blocked_domain_fetch.md)
- [`reference/cli_tool_mode.md`](web-tools/reference/cli_tool_mode.md)
- [`reference/playwright_patterns.md`](web-tools/reference/playwright_patterns.md)
- [`reference/webwright.md`](web-tools/reference/webwright.md)
- [`reference/webwright_workflow.md`](web-tools/reference/webwright_workflow.md)

## 工具三：受封鎖網域取回（Wayback 代抓）+ Google Forms 解析

目標網域被本機代理白名單封鎖時，改由 archive.org Save Page Now 代抓，
並從 Google Forms 內嵌的 `FB_PUBLIC_LOAD_DATA_` JSON 還原題目、題型、選項與必填旗標。

---

## 25. cv-job-application
[cv-job-application/SKILL.md](cv-job-application/SKILL.md)

# cv-job-application — 履歷投遞（中華電信 / 台積電）

在 Windows 上用 Playwright + CDP 自動化操作**中華電信人才招募網**（`https://rmis.cht.com.tw/portal/jobs/`）填寫報名表與上傳附件，
並處理台積電人事資料表（去識別化、簡報改字轉 PDF）。

## 專案位置與資料夾結構

---

## 26. micron-job-search
[micron-job-search/SKILL.md](micron-job-search/SKILL.md)

# Micron Job Search — 台中職缺抓取與分析

Micron 職缺查詢、分類、条件解析、履歷格式研究與報告產出的一條龍流程。

## 關鍵前提：網站架構

---

## 27. resume-cloudflare-maintenance
[resume-cloudflare-maintenance/SKILL.md](resume-cloudflare-maintenance/SKILL.md)

# Resume 01 maintenance

## Locate the project

Current Windows project root:
`<USERPROFILE>\Documents\Codex\2026-09-26\https-codotx-com-news-claude-code`

---

## 28. taobao-cost
[taobao-cost/SKILL.md](taobao-cost/SKILL.md)

# taobao-cost-fill — 淘寶費用計算明細填寫

## 目的
把依序編號的訂單卡片（含商品名稱、實付金額、物流、重量）填入既有的「淘寶費用計算明細」Excel 樣板（`*-taobao-淘寶-R0.xlsx`），依序寫入商品列，並另存成 `*-taobao-淘寶-R1.xlsx`。

## 前置需求（依賴）
- Python 3 + openpyxl，安裝於本 skill 專用 venv：
  ```bash
  cd <skill>/taobao-cost-fill
  python3 -m venv .venv
  .venv/bin/pip install openpyxl
  ```
- 執行時一律用 `.venv/bin/python`。

子功能參考文件：

- [`reference/taobao-order-extract.md`](taobao-cost/reference/taobao-order-extract.md)

---

## 29. yd7148-portfolio-deploy
[yd7148-portfolio-deploy/SKILL.md](yd7148-portfolio-deploy/SKILL.md)

# yd7148 個人網站維運（v1 / v2 / v3）

三個獨立的 Astro 靜態站，部署在 GitHub Pages。**同一份履歷內容、三種版面。**

專案根目錄：`<PROJECT_ROOT_B>\2026-09-CV\`（**撰寫時機器的路徑，可能不存在**；
執行前先確認，或依 repo 名稱 `cv1`／`cv2`／`cv3` 重新 clone。
注意本機 clone 的資料夾名**必須**與 repo 同名，否則 `fix-base.mjs` 會算錯 base 前綴）

---

## 30. astro-dev
詳見 [astro-dev/SKILL.md](astro-dev/SKILL.md)。

\|- Build and debug Astro sites: content collections, islands architecture, rendering modes, and image/SEO bas…

---

## 31. cloudflare-platform
詳見 [cloudflare-platform/SKILL.md](cloudflare-platform/SKILL.md)。

Use when building or deploying on Cloudflare's core platform — Workers, Pages, KV, R2, D1, AI, or networking…

---

## 32. github-skill-sync
[github-skill-sync/SKILL.md](github-skill-sync/SKILL.md)

# github-skill-sync — 本機與 GitHub Skills 同步

Repo 使用根目錄的 `<skill-name>/SKILL.md`，本機安裝仍使用 `skills/<skill-name>/SKILL.md`。
分類與用途見 Repo 根目錄 README.md；所有 skill 資料夾都直接放在 Repo 根目錄。

## 同步前

---

## 33. mac-disk-cleanup
詳見 [mac-disk-cleanup/SKILL.md](mac-disk-cleanup/SKILL.md)。

掃描與清理 macOS 磁碟空間：定位大目錄（家目錄、Applications、/Library/Application Support、CloudStorage、/private/var）、辨識可安全刪除的快取與孤兒…

---

## 34. network-port-check
[network-port-check/SKILL.md](network-port-check/SKILL.md)

# network-port-check

監測本機對外網路連線狀態，並針為「只有單一網站連不上」時的責任归因。
無需安裝任何套件（PowerShell 5.1 + 內建 curl.exe）。

## When to use

- 「測來對 PORT」「哪些 port 通」「哪些站會被擋」
- 「無法 RDP 進來」「SSH 連不上」「遠端桌面」
- 「某個網站連不上」「這個網址下不了」「是誰的問題」
- 寫稍 TLS / MITM 、測試延迟與上下載頱廣

## 全域相对分流（先做這一步）

| 征狀 | 走哪一條 |
|---|---|
| **大量**網站連不上 | 五項檢查（port 矩陣） |
| **只有 1～2 個**網站連不上 | 單點归因（本章） |

⚠ 常見誤判：看到單一網站失敗就說「被火焦牌擋」。
火焦牌不會只挑某個網域擋——**單點失敗幾乎都是服務端的問題**。

## 單點归因：分組對照

**最有價值的證據不是那個失敗的網站，而是它的同業對照組。**

實測範例（夸克雸盤）：

\❌ pan.quark.cn      203.119.169.79   CN/Hebei  AS37963   不通
✅ www.quark.cn       47.246.165.152  SG        AS45102   通   ← 同一間公司
✅ www.aliyun.com     47.88.128.4     SG        AS45102   通   ← 同一集團
\
同一台電腦、同一條網路、同一家公司，**官網通而雲盤不通**。
這在邏輯上直接排除本機火焦牌與 ISP——它們不會区分同公司的不同站台。

## 判讀速查

| 對照組 | 目標 | 結論 |
|-------|------|------|
| 全通 | 不通 | **服務端問題** |
| 全不通 | 不通 | 本機／網路層（回主流程排查） |
| 部分通 | 不通 | 看 IP 段／GeoIP 的公通點 |

若目標 IP 的 GeoIP 落在**與對照組不同的國家／ASN**（例如 CN 而非 SG），
即為服務商 **geo-routing 把你的流量派到不對外開放的機房**。

## 命令

\\powershell
.\scripts
un-all.ps1                                              # 一鍵完整檢查
.\scripts	est-single-host.ps1 -Target pan.quark.cn     -Control www.quark.cn,www.aliyun.com                      # 單點归因
\

---

## 35. opencode-session-auto-name
[opencode-session-auto-name/SKILL.md](opencode-session-auto-name/SKILL.md)

# opencode-session-auto-name — Session 標題自動命名

讓 opencode 的 session 名稱自動取自「第一次使用者 prompt 的總結」或「進行中 todo」，
解決原生開新 session 只有 `New session - ...` 泛型標題的困擾。

## 已安裝設定（本機，2026-09-21）

---

## 36. opencode-usage
[opencode-usage/SKILL.md](opencode-usage/SKILL.md)

# OpenCode Usage Monitor

Full documentation, metric definitions, and rationale: **[README.md](README.md)**
(資料來源、欄位定義、門檻訂定依據、花費模型、Telegram 設定、教學筆記)

Read-only observability for the local OpenCode installation. Never writes to
`opencode.db`, `auth.json`, or any OpenCode config.

---

## 37. py-binary-deps
詳見 [py-binary-deps/SKILL.md](py-binary-deps/SKILL.md)。

Use when a CLI tool or native binary must be installed on this machine — ffmpeg, yt-dlp, ffprobe, node, uv, r…

---

## 38. comfyui-qwen-image-edit
[comfyui-qwen-image-edit/SKILL.md](comfyui-qwen-image-edit/SKILL.md)

# comfyui-qwen-image-edit — ComfyUI + Qwen-Image-2.1 改圖

用 ComfyUI 的 Qwen-Image-2.1 做圖像編輯（改圖/換裝/服裝轉移/多圖參考）與文生圖。
2.1 是統一模型，同一份權重依舊做 t2i 與 edit，**不需另外下載 edit 版權重**。

## 兩個會靜默失敗的陷阱

1. **文字編碼器選錯** → 輸出滿版雜訊：
   `qwen3.5_9b_qwen_image_2.1_pe_i2i` 會被偵測成 `QWEN35_9B`，
   在 `comfy/sd.py` 更早的分支就被攔截，繞過 `QwenImage21Tokenizer`，
   缺少 `keep_vision` / `image_slots` → DiT 拼接 latent 位置全錯。
   正確用 `qwen3vl_8b_int8_convrot.safetensors`。
2. **V3 autogrow 插槽格式** → 參考圖被靜默丟棄：
   API 必須用扁平點號鍵 `"images.image_1"`，
   用巢狀 dict 會被靜默丟棄、流程退化成純文生圖、保留度全失。

兩者都**不報錯、照樣出圖**，只有用輸出尺寸反推才得知。

## 官方參數

`cfg`=1、`resolution`=0、`steps`=25、`euler`/`simple`，
prompt 內以 `<image1>` / `<image2>` 指代參考圖。

## 產出物

`workflows/` 含 UI 格式（可拖進 ComfyUI）與 API 格式工作流；
`scripts/run_wf.py` 為執行器。

---

## 39. mate-engine
[mate-engine/SKILL.md](mate-engine/SKILL.md)

# Mate Engine — 下載執行 + 動作數量擴充（Idle / Dance）

Mate Engine（伙伴引擎）是一款**免費、輕量、開源**的 Windows 桌面寵物（Desktop Pet）軟體，
是 **Desktop Mate 的免費替代品**：不綁商業角色模型、支援**自訂 VRM 角色**、可模組化（Mod）、
開源（GNU AGPL v3 + MateProv2 License），且比 Desktop Mate **更省資源**。

官方（非官方社群維護）GitHub：**https://github.com/shinyflvre/Mate-Engine**
→ 下載公開發行版 ZIP，解壓後執行 `MateEngineX.exe`。

## 動作數量擴充（Idle / Dance）

針對已編譯 Unity（Mono）的 Mate Engine X（`MateEngineX.exe`）——**無原始碼**，只能改
`Assembly-CSharp.dll`，把 BlendTree 中**已存在但被常數寫死而沒輪播**的動畫全部啟用：

- `totalIdleAnimations` 10 → **19**（clipID 0..18；再往上會混入 9 個男性 HUS_IDLE）
- `DANCE_CLIP_COUNT` 5 → **13**（clipID 42..54）
- 兩者**僅由 `.ctor` 寫入** → patch ctor 即生效
- ⚠️ 這是**開關不是加檔**，動畫資源本來就在 `sharedassets0.assets`；
  若要的是特定 MMD 舞蹈，屬於外部 `.unity3d` 匯入 `StreamingAssets\CustomDances\`，是另一回事
- ⚠️ 免費（GitHub）版**沒有 Steam Workshop**

完整流程（dnfile+dncil 反組譯 → UnityPy 驗證 BlendTree → Mono.Cecil 重寫 IL → dnfile 全量驗證）、
常見陷阱，見 [mate-engine/reference/anim-patch.md](mate-engine/reference/anim-patch.md)。
工具鏈用 [mate-engine/scripts/rebuild_tools.ps1](mate-engine/scripts/rebuild_tools.ps1) 重建
（`%TEMP%\opencode` 下的工具會被系統 Temp 清理抹掉）。

---

## 附錄：OpenCode 本機環境設定

本機 OpenCode Desktop App 環境設定總覽：**LSP（方案 2 精準開啟）**、**TUI 外掛（oc-plugin-rainbow）**、
**瀏覽器 MCP 固定 profile**。三項修改後皆需**完全重啟** OpenCode 才生效。

---

### LSP（精準開啟 方案 2）

本機已啟用 **LSP 精準開啟（方案 2）**：僅啟用 `typescript`、`pyright`、`yaml-ls`、`bash`
四個語言伺服器。啟用後 agent 可獲得 **`lsp` 工具**（goToDefinition、findReferences、hover、
documentSymbol、workspaceSymbol、goToImplementation、callHierarchy…）與**語言伺服器診斷回饋**
（診斷訊息自動流入 agent loop）。

#### 啟用開關（兩個都要）

| 開關 | 設定 | 位置 |
|------|------|------|
| ① `lsp` 工具 | 使用者層級環境變數 `OPENCODE_EXPERIMENTAL_LSP_TOOL=true`（或 `OPENCODE_EXPERIMENTAL=true`） | 系統內容 → 環境變數 |
| ② LSP server | `"lsp": { ... }`（見下） | `~/.config/opencode/opencode.jsonc` |

#### 設定內容

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "typescript": {},
    "pyright": {},
    "yaml-ls": {},
    "bash": {}
  }
}
```

OpenCode 在**讀到對應副檔名的檔案**且**必要條件滿足**時才啟動該伺服器（不會全載）。

| LSP | 副檔名 | 必要條件 | 本機狀態 |
|-----|--------|----------|----------|
| typescript | .ts/.tsx/.js/.jsx/.mjs/.cjs/.mts/.cts | 該專案需有 `typescript` 依賴 | ✅ Node 22 |
| pyright | .py/.pyi | 全域安裝 `pyright` | ✅ `npm i -g pyright`（已裝） |
| yaml-ls | .yaml/.yml | 自動下載 yaml-language-server | ✅ 自動下載 |
| bash | .sh/.bash/.zsh/.ksh | 自動下載 bash-language-server | ✅ 自動下載 |

#### 安裝／維護

```bash
npm i -g pyright                                     # pyright（本機已安裝）
cd <某個 TS/JS 專案> && npm i -D typescript          # typescript LSP 吃「專案自身」的 typescript 依賴
```

改完 `opencode.jsonc` 或環境變數後，需**完全重啟** OpenCode Desktop App 才生效。

#### 其他設定選項（參考）

- `"lsp": true` → 全開（所有內建 server）
- `"lsp": false` → 全關（預設值）
- `"lsp": { "typescript": { "disabled": true } }` → 全開但排除特定 server
- 自訂 server：`command` / `extensions` / `env` / `initialization` / `disabled`

> **未啟用的理由**：`jdtls`（Java）需 JDK 21+，而本機僅有 Java 8（本機既有 Java 應用程式使用）不適用；
> gopls / rust / lua-ls / ruby-lsp / php intelephense / clangd 等對應工具鏈未安裝，用不到就不自動下載，
> 避免浪費記憶體與啟動時間（官方 Best Practices 建議不要無腦全開）。
> `.ps1`（PowerShell）與 `.md` 目前沒有對應內建 LSP。

---

### TUI 外掛：oc-plugin-rainbow（彩虹特效）

TUI 外掛 oc-plugin-rainbow 為 OpenCode 終端介面加入**主題感知彩虹後製**：中性文字前景動畫色帶
+ 可選背景色調 + 內建設定對話框。需 OpenCode `>=1.3.14`。

設定檔：`~/.config/opencode/tui.json`

```jsonc
{
  "$schema": "https://opencode.ai/tui.json",
  "plugin": [
    ["oc-plugin-rainbow", { "enabled": true, "fg": true, "bg": true, "speed": 0.008, "turns": 3, "glow": 0.05 }]
  ]
}
```

常用選項：`enabled`（總開關）、`fg` / `bg`（文字／背景動畫）、`speed`（0–0.03）、`turns`（0.25–8）、
`glow`（0–0.15）、`keybinds.logo_splash`（預設 `ctrl+shift+r`，觸發白閃 logo 畫面）。

**安裝方式（本機已裝，v0.1.1）**，三選一：

```bash
opencode plugin oc-plugin-rainbow                             # CLI 安裝（官方方式）
npm install --prefix ~/.cache/opencode oc-plugin-rainbow@0.1.1 # 直接裝進 TUI 外掛快取（本機用此法）
```

或 TUI 內 `Ctrl+P → Install Plugin` 互動安裝。

微調：對話框輸入 `/rainbow-settings`（或 `Ctrl+P → Rainbow settings`）即時調整，設定存本機。

---

### 瀏覽器 MCP 固定 profile（跨專案共用登入）

Playwright MCP 預設按「工作區 hash」建立 profile
（`%USERPROFILE%\AppData\Local\ms-playwright\mcp-{channel}-{workspace-hash}`），
**不同專案 = 不同 profile = 每次都是未登入／空帳號**。解法：指定固定 `--user-data-dir`。

`~/.config/opencode/opencode.jsonc`：

```jsonc
"mcp": {
  "playwright": {
    "type": "local",
    "command": ["npx", "-y", "@playwright/mcp@latest", "--user-data-dir=<user>\\.cache\\opencode-browser-profiles\\playwright"],
    "enabled": true
  },
  "chrome-devtools": {
    "type": "local",
    "command": ["npx", "-y", "chrome-devtools-mcp@latest", "--autoConnect"],
    "enabled": true
  }
}
```

- **Playwright MCP** → 固定 profile `~/.cache/opencode-browser-profiles/playwright`，**所有專案共用同一份登入狀態**。
- **chrome-devtools MCP** → 維持 `--autoConnect`：自動連到使用者正在執行的 Chrome 預設 profile，
  直接沿用日常 Chrome 的登入（需 Chrome 144+，且已於 `chrome://inspect/#remote-debugging` 啟用遠端除錯）。
- ⚠️ **兩個 MCP 不可共用同一個 profile 目錄**（Chrome profile 一次只能被一個實例鎖定）；
  需多開並行 MCP 客戶端時，Playwright 各自指定不同 `--user-data-dir` 或加 `--isolated`。

---

### 生效與驗證

改完設定都要**完全重啟** OpenCode Desktop App：

- LSP：agent 出現 `lsp` 工具、診斷回饋流入對話
- Rainbow：`Ctrl+P → Rainbow settings`、`Ctrl+Shift+R`（logo flash）
- Playwright profile：登入任一網站 → 換到另一專案 → 仍保持登入

---

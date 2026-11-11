# OpenCode Skills

OpenCode 本機 Skills 收藏庫。所有 skill 皆為 MIT 授權，適用於 opencode agents。

> 📖 每支 skill 的完整功能、適用時機、運作流程與產出，請參閱 **[SKILLS.md](SKILLS.md)**。

---

## 公開版說明

此 repo 為 [yd7148/OpenCode_skill](https://github.com/yd7148/OpenCode_skill) 的**公開子集**。

| 面向 | 說明 |
|------|------|
| 收錄內容 | 通用型 OpenCode skills（工具型、流程型、參考資料型） |
| 未收錄 | 個人／雇主專屬內容：維運紀錄、內網拓撲紀錄、公司專用自動化、薪資分析工具 |
| 資料處理 | 所有真實內網位址、主機名稱、憑證、公司識別字串已替換為佔位符（`<HOST_IP>`、`<CORP_NAME>`…） |
| 授權 | 每個 skill 的 frontmatter 各自標示；本 repo 另附 [LICENSE](LICENSE) |

> **為什麼分兩個 repo？** 原始 repo 同時存放 skill 收藏與個人維運紀錄，
> 後者含公司內部網路拓撲與專用自動化細節，不適合公開。
> 分離後既保有公開分享的價值，也不讓工作紀錄外流。


## 功能分類

<!-- gen:readme-index:start -->
共 **41 個 skill** 資料夾直接放在 Repo 根目錄；下方依功能分成 8 類。

| 分類 | 數量 |
|---|---:|
| 工程模擬與 CAD | 2 |
| 文件與會議紀錄 | 10 |
| 考試與解題 | 1 |
| 影音下載、處理與分析 | 7 |
| 瀏覽器與桌面自動化 | 6 |
| 辦公、求職與商務 | 5 |
| 開發工具與 Skill 管理 | 8 |
| 圖像生成與桌寵 | 2 |

### 工程模擬與 CAD

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`dwg-to-dxf`](dwg-to-dxf/SKILL.md) | 🪟 | Convert AutoCAD DWG files to DXF format using ODA File Converter, then perform detailed geometric and metadat…  | 額外系統工具：ODA File Converter、Python ezdxf |
| [`sd-webui-vae-fix`](sd-webui-vae-fix/SKILL.md) | 🪟 | 修復 AUTOMATIC1111 Stable Diffusion WebUI（A1111 / sd.webui）「無法切換」檢查點或 VAE 的錯誤（sd_model_checkpoint / sd_vae 選擇失敗…  | WebUI 環境：webui 內建 Python（torch + safetensors） |

### 文件與會議紀錄

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`docx-edit`](docx-edit/SKILL.md) | 🪟 | Use when the user asks to read, edit, convert, extract from, or generate Word .docx files (新增/修改/取代 Word 內容、表…  | 純 Python：python-docx、pywin32（需 MS Word COM） |
| [`image-to-pdf`](image-to-pdf/SKILL.md) | 🍎 | 將一個資料夾內的圖片（PNG/JPG 等）合併成單一 PDF，每一頁一張圖片、依檔名順序排列，使用 Pillow 離線產生。Use when asked to "圖片轉 PDF", "圖片合併成 PDF", "每一頁一…  | 純 Python：Pillow |
| [`line-group-export-analysis`](line-group-export-analysis/SKILL.md) | 🍎 | 匯入並分析 LINE 群組聊天記錄（手機「匯出聊天記錄」產生的 txt/zip，或以 Browser Control 從 LINE Web 分頁逐段捲動擷取），產出每人發文量與頻率、活躍時段、回覆互動網路、訊息長度分布…  | 未分類 |
| [`md-to-pdf`](md-to-pdf/SKILL.md) | 🍎 | 將繁體中文 Markdown 說明檔渲染成排版精美的 A4 多頁 PDF（標題、表格、代碼區塊、引言、頁碼），使用 Pillow + 微軟正黑體離線產生，不需網路。Use when asked to "寫一個MARKD…  | 純 Python：Pillow（中文字體自動偵測） |
| [`meeting-transcript-summary`](meeting-transcript-summary/SKILL.md) | 🍎 | 將一場會議的「原始時間戳逐字稿」（*_timestamp.txt，語音辨識輸出）彙總成詳盡繁體中文主管會議紀錄摘要（含各主管問題、部屬答覆、目標與代辦事項），存成 <BASE>_會議彙總.md。Use when ask…  | 無額外依賴（opencode 內建工具） |
| [`news-weekly-docx-move`](news-weekly-docx-move/SKILL.md) | 🪟 | Use when the user asks to bulk-move, copy, collect, or sync the weekly news review .docx files (個人週報 新聞(OK).d…  | 無額外依賴（PowerShell + 網路分享） |
| [`pdf-reader`](pdf-reader/SKILL.md) | 🍎 | 讀取 PDF 檔案的內容並輸出成 Markdown 摘要報告。文字型 PDF 用 PyMuPDF 直接抽取（含中文）；掃描/圖片型 PDF 自動渲染成 PNG 並以 RapidOCR 辨識；輸出以 opencc 轉為繁…  | 重型機器學習：venv（PyMuPDF、RapidOCR、opencc） |
| [`pptx`](pptx/SKILL.md) | 🍎 | Use when generating or manipulating PowerPoint presentations programmatically.  | npm 套件／純 Python：pptxgenjs、python-pptx |
| [`xlsx`](xlsx/SKILL.md) | 🍎 | Use when creating, reading, or manipulating Excel workbooks programmatically with formulas, charts, and forma…  | npm 套件／純 Python：exceljs、openpyxl |
| [`zh-text-polish`](zh-text-polish/SKILL.md) | 🍎 | 繁體中文錯字校對與文句潤飾（會議紀錄、公文、技術報告），輸出錯字對照表＋修訂全文＋Markdown表格與Mermaid流程圖。Use when asked to "確認錯字", "文句潤飾", "會議紀錄校對", "公…  | 無額外依賴（opencode 內建工具） |

### 考試與解題

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`exam-report`](exam-report/SKILL.md) | 🪟 | Use when the user needs to process 國營事業 / 台電 / 中油 / 中水 / 台糖 recruitment exam PDFs.  | 重型機器學習：venv（pymupdf、EasyOCR、Qwen2.5-VL、ngspice） |

### 影音下載、處理與分析

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`on24-video-download`](on24-video-download/SKILL.md) | 🍎 | 下載 ON24 線上研討會活動（event.on24.com）的影片、投影片與字幕，並從下載的主影片自動提取「投影片 PDF / 投影片影片 / 時間軸摘要」。涵蓋公開媒體組態 API、download/CDN URL…  | 額外系統工具：curl、ffmpeg、Pillow、RapidOCR |
| [`takeout-exif-merge`](takeout-exif-merge/SKILL.md) | 🍎 | Use when the user asks to merge Google Photos Takeout supplemental-metadata.json sidecar files into the same-…  | 額外系統工具：ExifTool |
| [`tts`](tts/SKILL.md) | 🍎 | 使用 Microsoft Edge 的 edge-tts 將文字轉成高品質語音（Text-to-Speech），支援繁體中文、簡體中文、粵語與多國語言與多種聲音。可將文字轉成 mp3 語音檔，並可調整速率、音量、音調，…  | 純 Python：edge-tts（+ ffmpeg） |
| [`twii-excel-fill`](twii-excel-fill/SKILL.md) | 🍎 | Use when the user wants to fill in 台股加權指數（發行量加權股價指數）每日漲跌點數 into an Excel 活頁簿（例如「2026-10-02-股價+加密+藥.xlsx」的分頁「1…  | 純 Python：openpyxl |
| [`video-analysis`](video-analysis/SKILL.md) | 🍎 | Use when the user wants to analyse or process 影片 (course videos, YouTube live class sessions, screen recordin…  | 重型機器學習：venv（whisper、RapidOCR、PyMuPDF、opencc）、ffmpeg、yt-dlp |
| [`yt-batch-download`](yt-batch-download/SKILL.md) | 🍎 | 批次下載 YouTube 影片（1080p 最高畫質），支援自訂檔名、cookies 匯入、SSL 修復、JS runtime 設定。Use when asked to "下載YouTube影片", "批次下載YT",…  | 額外系統工具：yt-dlp、browser_cookie3、ffmpeg、deno |
| [`yt-upload`](yt-upload/SKILL.md) | 🍎 | 透過 Playwright 操作 YouTube Studio，將本機影片上傳並公開發布為 YouTube 影片。支援填寫詳細的標題、說明、標籤、主題標籤，設定目標觀眾（非兒童專屬）、瀏覽權限（公開/不公開/私人），並…  | 瀏覽器自動化：Playwright |

### 瀏覽器與桌面自動化

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`browser-control`](browser-control/SKILL.md) | 🍎 | Drive the user's existing Chromium-family browser with deterministic Playwright.  | 瀏覽器自動化：browser-control CLI / MCP、ffmpeg |
| [`browser-site-guides`](browser-site-guides/SKILL.md) | 🍎 | Use when asked to "操作 gmail、linkedin、amazon、tiktok、xiaohongshu、bbc-news、google-maps 等特定網站"、或需要該網站的反爬／驗證／流程細節、…  | 瀏覽器自動化：browser-control CLI（擴充須自備，無額外安裝） |
| [`browser-stack-routing`](browser-stack-routing/SKILL.md) | 🍎 | 決定本機五套瀏覽器／桌面自動化該用哪一套（browser-control、opencode-browser、browser-skill/bsk、chrome-devtools、open-computer-use），並強…  | 瀏覽器自動化：bsk CLI、browser-control MCP、opencode-browser 外掛（三軌擇一） |
| [`open-computer-use`](open-computer-use/SKILL.md) | 🍎 | Platform-neutral guidance for using Open Computer Use, the open-source Computer Use MCP server and CLI for ma…  | npm 套件：open-computer-use（macOS 14+ 需授權） |
| [`opencode-browser`](opencode-browser/SKILL.md) | 🍎 | 用 OpenCode 外掛 `@different-ai/opencode-browser`（native messaging + broker）控制使用者「既有」的 Chrome／Edge／Chromium 視窗，沿…  | 瀏覽器自動化：OpenCode 外掛 @different-ai/opencode-browser + Node.js |
| [`web-tools`](web-tools/SKILL.md) | 🍎 | Use when the user needs to fetch web pages or automate a browser.  | 瀏覽器自動化：Crawl4AI venv、Playwright（Firefox） |

### 辦公、求職與商務

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`cv-job-application`](cv-job-application/SKILL.md) | 🪟 | Use when 投遞或填寫 中華電信/台積電 線上履歷、要操作 rmis.cht.com.tw 報名表（自動填表、附件上傳、狀態檢核）、要沿用已保存的 Chrome 登入資訊（.pw-profile）登入、需要把台積…  | 瀏覽器自動化：Playwright CDP、ddddocr、EasyOCR、pymupdf |
| [`micron-job-search`](micron-job-search/SKILL.md) | 🍎 | Use when the user wants to search, filter, categorize, or analyze Micron Technology job openings (careers.mic…  | 瀏覽器自動化：Playwright、Pillow |
| [`resume-cloudflare-maintenance`](resume-cloudflare-maintenance/SKILL.md) | 🍎 | 維護劉士禎的 Resume 01 個人履歷網站與 Cloudflare Workers 靜態部署；用於本專案更新中英內容、保留舊版、建立發布副本、調整 workers.dev 網址或還原。不是通用網站建置 Skill。  | 無額外依賴（純 git / wrangler 流程） |
| [`taobao-cost`](taobao-cost/SKILL.md) | 🍎 | Use when the user works with 淘obao (Taobao) exported order data or 淘寶費用計算明細 spreadsheets.  | 純 Python：openpyxl |
| [`yd7148-portfolio-deploy`](yd7148-portfolio-deploy/SKILL.md) | 🪟 | Use when 維護／部署／改網址／改路由／處理個資 for 劉士禎的三個個人網站（Astro 7 + Tailwind v4 + GitHub Pages + Actions 自動部署）—— repo `cv1`（…  | 雲端服務：Node、GitHub Pages、Cloudflare |

### 開發工具與 Skill 管理

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`astro-dev`](astro-dev/SKILL.md) | 🍎 | \|- Build and debug Astro sites: content collections, islands architecture, rendering modes, and image/SEO bas…  | 純知識（來源 opencodeskills.dev） |
| [`cloudflare-platform`](cloudflare-platform/SKILL.md) | 🍎 | Use when building or deploying on Cloudflare's core platform — Workers, Pages, KV, R2, D1, AI, or networking…  | 雲端服務：wrangler / Cloudflare 帳號 |
| [`github-skill-sync`](github-skill-sync/SKILL.md) | 🍎 | 同步本機 OpenCode skills（`~/.config/opencode/skills/`）與 GitHub 上的 `yd7148/OpenCode_skill` 收藏庫。本 skill 同時管理**下載（Gi…  | 無額外依賴（git / rsync / ssh） |
| [`mac-disk-cleanup`](mac-disk-cleanup/SKILL.md) | 🍎 | 掃描與清理 macOS 磁碟空間：定位大目錄（家目錄、Applications、/Library/Application Support、CloudStorage、/private/var）、辨識可安全刪除的快取與孤兒…  | 無額外依賴（macOS 內建 du / df / rm） |
| [`network-port-check`](network-port-check/SKILL.md) | 🍎 | 檢查本機對外網路連線狀態（Windows PowerShell 與 macOS bash 雙版本）：哪些 TCP port 通、哪些被防火牆擋、遠端服務（RDP/SSH/VNC）能否接通、有哪些網站被擋、TLS 是否被…  | 無額外依賴（macOS 需 curl / nc / dig / openssl / swiftc） |
| [`opencode-session-auto-name`](opencode-session-auto-name/SKILL.md) | 🍎 | 讓 opencode 的 session 標題自動以「第一次 prompt 的總結」命名（或進行中 todo）。使用本 skill 內建的 OpenCode V2 plugin（0 Token、純規則式、與模型無關、零…  | npm 套件：opencode-auto-name（0 Token） |
| [`opencode-usage`](opencode-usage/SKILL.md) | 🍎 | Monitor and report OpenCode usage, quota, and local resource consumption.  | 純 Python：標準庫（跨平台） |
| [`py-binary-deps`](py-binary-deps/SKILL.md) | 🍎 | Use when a CLI tool or native binary must be installed on this machine — ffmpeg, yt-dlp, ffprobe, node, uv, r…  | 無額外依賴（Python + pip / uv；ffmpeg 需於 PATH） |

### 圖像生成與桌寵

| Skill | 平台 | 一句話說明 | 依賴／平台 |
|---|:--:|---|---|
| [`comfyui-qwen-image-edit`](comfyui-qwen-image-edit/SKILL.md) | 🍎 | 用 ComfyUI + Qwen-Image-2.1 做圖像編輯（改圖／換裝／服裝轉移／多圖參考）與文生圖，產出可直接拖入 ComfyUI 的工作流 JSON，並用 /prompt API 批次執行。涵蓋兩個會「不報錯…  | 額外系統工具：ComfyUI + Qwen-Image-2.1 模型、/prompt API |
| [`mate-engine`](mate-engine/SKILL.md) | 🍎 | Mate Engine / Mate Engine X（免費輕量桌面寵物、Desktop Mate 替代品）的下載、安裝執行，以及動作數量擴充（把 Assembly-CSharp.dll 的 totalIdleAnim…  | 額外系統工具：dnfile / dncil / UnityPy（動畫擴充） |

<!-- gen:readme-index:end -->

## 預設不安裝（本機刻意排除）

<!-- gen:readme-not-installed:start -->
下列 skill 保留在 Repo 供參考，但**本機 `~/.config/opencode/skills/` 刻意不安裝**；
`github-skill-sync` 下載時會自動跳過。

| Skill | 類別 | 原因 |
|---|---|---|

排除規則見 [`github-skill-sync`](github-skill-sync/SKILL.md) 的下載章節。

<!-- gen:readme-not-installed:end -->

## 安裝

Repo 路徑為 `<skill-name>/`。例如根目錄的 `pdf-reader/` 安裝成 `skills/pdf-reader/`。

將任一 skill 資料夾複製到 `~/.config/opencode/skills/<skill-name>/`（或 `.opencode/skills/<skill-name>/`）即可使用。

各 skill 的 Python 依賴建議安裝於**各 skill 資料夾專用 venv**（`<skill>/.venv`），不會影響系統全域 Python：

```bash
cd ~/.config/opencode/skills/<skill-name>
python3 -m venv .venv
.venv/bin/pip install <所需套件>
```

> 註：repo 內容同時適用 Windows（PowerShell 5.1，`py` launcher）與 macOS。`md-to-pdf` 已內建中文字體自動偵測，macOS 使用 STHeiti、Windows 使用微軟正黑體（msjh.ttc）。



## 依賴／平台總覽

<!-- gen:readme-deps:start -->
依賴資訊由 `scripts/gen_index.py` 的 `DEPENDENCY` 對照表產生，維護時請改該表。

| 類型 | Skill |
|---|---|
| 無額外依賴 | `github-skill-sync`、`mac-disk-cleanup`、`meeting-transcript-summary`、`network-port-check`、`news-weekly-docx-move`、`py-binary-deps`、`resume-cloudflare-maintenance`、`zh-text-polish` |
| 純 Python（跨平台） | `docx-edit`、`image-to-pdf`、`md-to-pdf`、`opencode-usage`、`taobao-cost`、`tts`、`twii-excel-fill` |
| 重型機器學習（各 skill 專用 venv） | `exam-report`、`pdf-reader`、`video-analysis` |
| 需額外系統工具 | `comfyui-qwen-image-edit`、`dwg-to-dxf`、`mate-engine`、`on24-video-download`、`takeout-exif-merge`、`yt-batch-download` |
| 需 npm 套件 | `open-computer-use`、`opencode-session-auto-name`、`pptx`、`xlsx` |
| 瀏覽器自動化 | `browser-control`、`browser-site-guides`、`browser-stack-routing`、`cv-job-application`、`micron-job-search`、`opencode-browser`、`web-tools`、`yt-upload` |
| 需 WebUI 環境 | `sd-webui-vae-fix` |
| 需雲端服務 | `cloudflare-platform`、`yd7148-portfolio-deploy` |
| **未分類（需補 DEPENDENCY）** | `astro-dev`、`line-group-export-analysis` |

<!-- gen:readme-deps:end -->

## OpenCode 本機環境設定

本收藏庫對應的 opencode 環境（Desktop App）已做以下設定：

1. **LSP 精準開啟（方案 2）** — `opencode.jsonc` 啟用 `typescript`、`pyright`、`yaml-ls`、`bash` 四個語言伺服器；以使用者環境變數 `OPENCODE_EXPERIMENTAL_LSP_TOOL=true` 開啟 `lsp` 工具（定義跳轉／找參考／診斷回饋）。安裝：`npm i -g pyright`；TS 專案需各自 `npm i -D typescript`。
2. **TUI 外掛 oc-plugin-rainbow** — `tui.json` 啟用彩虹特效，套件已裝進 `~/.cache/opencode/node_modules`（v0.1.1）。微調：`Ctrl+P → Rainbow settings`。
3. **瀏覽器 MCP 固定 profile** — Playwright MCP 指定 `--user-data-dir=~/.cache/opencode-browser-profiles/playwright`，所有專案共用登入（解決「空帳號／未登入」）；chrome-devtools 維持 `--autoConnect` 沿用日常 Chrome 登入。
4. **Session 標題自動命名（opencode-auto-name）** — `opencode.jsonc` 加入 plugin 陣列 `["opencode-auto-name", { "template": "{firstMessage}", "maxLength": 50 }]`，新 session 標題自動取第一個 prompt 的首句總結；純規則式、0 Token。原理與替代方案比較見 skill `opencode-session-auto-name`。

> 三項修改後皆需**完全重啟** OpenCode。詳細設定、選項與驗證方式：見 **[SKILLS.md 附錄](SKILLS.md)**。

設定檔本身的範本與「`opencode.jsonc` vs `AGENTS.md` 分工」說明見原始 repo 的 `opencode-env/` 目錄；
該目錄是範本，不是直接生效的檔案，需自行複製到 `~/.config/opencode/`。

## 個人履歷網站維護

- [resume-cloudflare-maintenance](resume-cloudflare-maintenance/SKILL.md)：Resume 01 中英內容維護、保留舊版與 Cloudflare 靜態部署。



## Skill 分類索引（41 個）

<!-- gen:readme-all:start -->
共 41 個 skill。

| Skill | 平台 | 說明 |
|---|:--:|---|
| [`astro-dev`](astro-dev/SKILL.md) | 🍎 | \|- Build and debug Astro sites: content collections, islands architecture, rendering modes, and image/SEO bas…  |
| [`browser-control`](browser-control/SKILL.md) | 🍎 | Drive the user's existing Chromium-family browser with deterministic Playwright.  |
| [`browser-site-guides`](browser-site-guides/SKILL.md) | 🍎 | Use when asked to "操作 gmail、linkedin、amazon、tiktok、xiaohongshu、bbc-news、google-maps 等特定網站"、或需要該網站的反爬／驗證／流程細節、…  |
| [`browser-stack-routing`](browser-stack-routing/SKILL.md) | 🍎 | 決定本機五套瀏覽器／桌面自動化該用哪一套（browser-control、opencode-browser、browser-skill/bsk、chrome-devtools、open-computer-use），並強…  |
| [`cloudflare-platform`](cloudflare-platform/SKILL.md) | 🍎 | Use when building or deploying on Cloudflare's core platform — Workers, Pages, KV, R2, D1, AI, or networking…  |
| [`comfyui-qwen-image-edit`](comfyui-qwen-image-edit/SKILL.md) | 🍎 | 用 ComfyUI + Qwen-Image-2.1 做圖像編輯（改圖／換裝／服裝轉移／多圖參考）與文生圖，產出可直接拖入 ComfyUI 的工作流 JSON，並用 /prompt API 批次執行。涵蓋兩個會「不報錯…  |
| [`cv-job-application`](cv-job-application/SKILL.md) | 🪟 | Use when 投遞或填寫 中華電信/台積電 線上履歷、要操作 rmis.cht.com.tw 報名表（自動填表、附件上傳、狀態檢核）、要沿用已保存的 Chrome 登入資訊（.pw-profile）登入、需要把台積…  |
| [`docx-edit`](docx-edit/SKILL.md) | 🪟 | Use when the user asks to read, edit, convert, extract from, or generate Word .docx files (新增/修改/取代 Word 內容、表…  |
| [`dwg-to-dxf`](dwg-to-dxf/SKILL.md) | 🪟 | Convert AutoCAD DWG files to DXF format using ODA File Converter, then perform detailed geometric and metadat…  |
| [`exam-report`](exam-report/SKILL.md) | 🪟 | Use when the user needs to process 國營事業 / 台電 / 中油 / 中水 / 台糖 recruitment exam PDFs.  |
| [`github-skill-sync`](github-skill-sync/SKILL.md) | 🍎 | 同步本機 OpenCode skills（`~/.config/opencode/skills/`）與 GitHub 上的 `yd7148/OpenCode_skill` 收藏庫。本 skill 同時管理**下載（Gi…  |
| [`image-to-pdf`](image-to-pdf/SKILL.md) | 🍎 | 將一個資料夾內的圖片（PNG/JPG 等）合併成單一 PDF，每一頁一張圖片、依檔名順序排列，使用 Pillow 離線產生。Use when asked to "圖片轉 PDF", "圖片合併成 PDF", "每一頁一…  |
| [`line-group-export-analysis`](line-group-export-analysis/SKILL.md) | 🍎 | 匯入並分析 LINE 群組聊天記錄（手機「匯出聊天記錄」產生的 txt/zip，或以 Browser Control 從 LINE Web 分頁逐段捲動擷取），產出每人發文量與頻率、活躍時段、回覆互動網路、訊息長度分布…  |
| [`mac-disk-cleanup`](mac-disk-cleanup/SKILL.md) | 🍎 | 掃描與清理 macOS 磁碟空間：定位大目錄（家目錄、Applications、/Library/Application Support、CloudStorage、/private/var）、辨識可安全刪除的快取與孤兒…  |
| [`mate-engine`](mate-engine/SKILL.md) | 🍎 | Mate Engine / Mate Engine X（免費輕量桌面寵物、Desktop Mate 替代品）的下載、安裝執行，以及動作數量擴充（把 Assembly-CSharp.dll 的 totalIdleAnim…  |
| [`md-to-pdf`](md-to-pdf/SKILL.md) | 🍎 | 將繁體中文 Markdown 說明檔渲染成排版精美的 A4 多頁 PDF（標題、表格、代碼區塊、引言、頁碼），使用 Pillow + 微軟正黑體離線產生，不需網路。Use when asked to "寫一個MARKD…  |
| [`meeting-transcript-summary`](meeting-transcript-summary/SKILL.md) | 🍎 | 將一場會議的「原始時間戳逐字稿」（*_timestamp.txt，語音辨識輸出）彙總成詳盡繁體中文主管會議紀錄摘要（含各主管問題、部屬答覆、目標與代辦事項），存成 <BASE>_會議彙總.md。Use when ask…  |
| [`micron-job-search`](micron-job-search/SKILL.md) | 🍎 | Use when the user wants to search, filter, categorize, or analyze Micron Technology job openings (careers.mic…  |
| [`network-port-check`](network-port-check/SKILL.md) | 🍎 | 檢查本機對外網路連線狀態（Windows PowerShell 與 macOS bash 雙版本）：哪些 TCP port 通、哪些被防火牆擋、遠端服務（RDP/SSH/VNC）能否接通、有哪些網站被擋、TLS 是否被…  |
| [`news-weekly-docx-move`](news-weekly-docx-move/SKILL.md) | 🪟 | Use when the user asks to bulk-move, copy, collect, or sync the weekly news review .docx files (個人週報 新聞(OK).d…  |
| [`on24-video-download`](on24-video-download/SKILL.md) | 🍎 | 下載 ON24 線上研討會活動（event.on24.com）的影片、投影片與字幕，並從下載的主影片自動提取「投影片 PDF / 投影片影片 / 時間軸摘要」。涵蓋公開媒體組態 API、download/CDN URL…  |
| [`open-computer-use`](open-computer-use/SKILL.md) | 🍎 | Platform-neutral guidance for using Open Computer Use, the open-source Computer Use MCP server and CLI for ma…  |
| [`opencode-browser`](opencode-browser/SKILL.md) | 🍎 | 用 OpenCode 外掛 `@different-ai/opencode-browser`（native messaging + broker）控制使用者「既有」的 Chrome／Edge／Chromium 視窗，沿…  |
| [`opencode-session-auto-name`](opencode-session-auto-name/SKILL.md) | 🍎 | 讓 opencode 的 session 標題自動以「第一次 prompt 的總結」命名（或進行中 todo）。使用本 skill 內建的 OpenCode V2 plugin（0 Token、純規則式、與模型無關、零…  |
| [`opencode-usage`](opencode-usage/SKILL.md) | 🍎 | Monitor and report OpenCode usage, quota, and local resource consumption.  |
| [`pdf-reader`](pdf-reader/SKILL.md) | 🍎 | 讀取 PDF 檔案的內容並輸出成 Markdown 摘要報告。文字型 PDF 用 PyMuPDF 直接抽取（含中文）；掃描/圖片型 PDF 自動渲染成 PNG 並以 RapidOCR 辨識；輸出以 opencc 轉為繁…  |
| [`pptx`](pptx/SKILL.md) | 🍎 | Use when generating or manipulating PowerPoint presentations programmatically.  |
| [`py-binary-deps`](py-binary-deps/SKILL.md) | 🍎 | Use when a CLI tool or native binary must be installed on this machine — ffmpeg, yt-dlp, ffprobe, node, uv, r…  |
| [`resume-cloudflare-maintenance`](resume-cloudflare-maintenance/SKILL.md) | 🍎 | 維護劉士禎的 Resume 01 個人履歷網站與 Cloudflare Workers 靜態部署；用於本專案更新中英內容、保留舊版、建立發布副本、調整 workers.dev 網址或還原。不是通用網站建置 Skill。  |
| [`sd-webui-vae-fix`](sd-webui-vae-fix/SKILL.md) | 🪟 | 修復 AUTOMATIC1111 Stable Diffusion WebUI（A1111 / sd.webui）「無法切換」檢查點或 VAE 的錯誤（sd_model_checkpoint / sd_vae 選擇失敗…  |
| [`takeout-exif-merge`](takeout-exif-merge/SKILL.md) | 🍎 | Use when the user asks to merge Google Photos Takeout supplemental-metadata.json sidecar files into the same-…  |
| [`taobao-cost`](taobao-cost/SKILL.md) | 🍎 | Use when the user works with 淘obao (Taobao) exported order data or 淘寶費用計算明細 spreadsheets.  |
| [`tts`](tts/SKILL.md) | 🍎 | 使用 Microsoft Edge 的 edge-tts 將文字轉成高品質語音（Text-to-Speech），支援繁體中文、簡體中文、粵語與多國語言與多種聲音。可將文字轉成 mp3 語音檔，並可調整速率、音量、音調，…  |
| [`twii-excel-fill`](twii-excel-fill/SKILL.md) | 🍎 | Use when the user wants to fill in 台股加權指數（發行量加權股價指數）每日漲跌點數 into an Excel 活頁簿（例如「2026-10-02-股價+加密+藥.xlsx」的分頁「1…  |
| [`video-analysis`](video-analysis/SKILL.md) | 🍎 | Use when the user wants to analyse or process 影片 (course videos, YouTube live class sessions, screen recordin…  |
| [`web-tools`](web-tools/SKILL.md) | 🍎 | Use when the user needs to fetch web pages or automate a browser.  |
| [`xlsx`](xlsx/SKILL.md) | 🍎 | Use when creating, reading, or manipulating Excel workbooks programmatically with formulas, charts, and forma…  |
| [`yd7148-portfolio-deploy`](yd7148-portfolio-deploy/SKILL.md) | 🪟 | Use when 維護／部署／改網址／改路由／處理個資 for 劉士禎的三個個人網站（Astro 7 + Tailwind v4 + GitHub Pages + Actions 自動部署）—— repo `cv1`（…  |
| [`yt-batch-download`](yt-batch-download/SKILL.md) | 🍎 | 批次下載 YouTube 影片（1080p 最高畫質），支援自訂檔名、cookies 匯入、SSL 修復、JS runtime 設定。Use when asked to "下載YouTube影片", "批次下載YT",…  |
| [`yt-upload`](yt-upload/SKILL.md) | 🍎 | 透過 Playwright 操作 YouTube Studio，將本機影片上傳並公開發布為 YouTube 影片。支援填寫詳細的標題、說明、標籤、主題標籤，設定目標觀眾（非兒童專屬）、瀏覽權限（公開/不公開/私人），並…  |
| [`zh-text-polish`](zh-text-polish/SKILL.md) | 🍎 | 繁體中文錯字校對與文句潤飾（會議紀錄、公文、技術報告），輸出錯字對照表＋修訂全文＋Markdown表格與Mermaid流程圖。Use when asked to "確認錯字", "文句潤飾", "會議紀錄校對", "公…  |

<!-- gen:readme-all:end -->

h-text-polish` skill 首次建立）與索引同步 |

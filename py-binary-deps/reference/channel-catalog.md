# PyPI 二進位套件盤查表（實測）

> 盤查日期：2026-10-22 ｜ 環境：Windows x64、Python 3.13.12、Company Proxy
> 方法：`pip download --no-deps --only-binary :all:` 取 wheel → 讀 wheel 內容清點
> `.exe` / `.so` / `.dylib`（可執行檔）與 `.dll` / `.pyd`（原生函式庫）→ 掃描 `.py` 中的下載網址。

---

## 一、可執行檔型（wheel 內含真正的 CLI）

這類是**本 skill 的核心**：安裝完就有可執行檔，不依賴任何外部下載。

| 套件 | 版本 | wheel 內可執行檔 | 用途 | 備註 |
|---|---|---|---|---|
| **`imageio-ffmpeg`** | 0.6.0 | `imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe` | **ffmpeg 7.1 CLI** | 本機首選備援管道 |
| **`uv`** | 0.13.5 | `uv.exe`、`uvw.exe`、`uvx.exe` | Python/套件管理 + 工具執行器 | `uv tool install` 走 PyPI，可用 |
| **`ruff`** | 0.17.1 | `ruff.exe` | Python linter / formatter | 極小（9.6 MiB） |
| **`aria2`** | — | `aria2c/bin/aria2c.exe` | 多執行緒下載器 | |
| **`playwright`** | 1.64.0 | `playwright/driver/node.exe` | **內含 Node v24.21.0** | 但 `playwright install chromium` 仍需下載瀏覽器 → 被封 |
| `pyinstaller` | — | `PyInstaller/bootloader/Windows-64bit-intel/run*.exe` | 打包用 bootloader | 內含的是 bootloader，非獨立工具 |
| `pywin32` | — | `Pythonwin.exe`、`pythonservice.exe` | COM/OLE 支援 | 另有 55 個 .pyd |

---

## 二、純 Python 型（0 二進位，pip 安裝即用）

| 套件 | 版本 | 用途 | 是否需要外部 ffmpeg |
|---|---|---|---|
| **`yt-dlp`** | 2026.10.21 | 影音下載 | **只在合併 video+audio 兩條 stream 時**需要 |
| `streamlink` | — | 串流直播擷取 | 選用 |
| `gallery-dl` | — | 圖庫批次下載 | 選用 |
| `sqlmap` | — | SQL 注入測試 | 否 |
| `pipx` | — | 隔離安裝 CLI 工具 | 否 |
| `pip-tools` / `pre-commit` / `hatch` | — | 開發流程 | 否 |
| `nodeenv` | — | 建立 node 虛擬環境 | 否 |
| `shimmy` | — | 把 CLI 轉成 Python 可呼叫 | 否 |
| `cx-freeze` | — | 打包 | 否 |
| **`pyffmpeg`** | 2.5.2.3.2 | ffmpeg 的 Python wrapper | **是 —— 本身不提供 ffmpeg CLI** |
| `ffmpeg-python` | — | ffmpeg 的 Python wrapper | **是** |

> `yt-dlp` 的重點：官方 wheel 是**純 Python**（1,059 個檔案、0 個二進位）。
> 網路上流傳的 `yt-dlp.exe` 是給沒有 Python 的環境用的單檔版本，
> 在本機走 `pip install yt-dlp` 反而是**唯一可行**的管道。

---

## 三、執行期下載型（❌ 本機不可用）

安裝會成功，但執行時會去被封鎖的網域抓檔案。

| 套件 | 版本 | 實際下載來源 | 判定 |
|---|---|---|---|
| **`static-ffmpeg`** | 3.0 | `github.com/zackees/ffmpeg_bins/raw/main/v8.0/win32.zip` 等 | ❌ `raw.githubusercontent.com` / release 資產被封 |
| **`ffmpeg-downloader`** | 0.5.3 | `api.github.com/repos/BtbN/FFmpeg-Builds`、`github.com/GyanD/codexffmpeg/releases/download/`、`www.gyan.dev` | ❌ 三個來源全部被封 |

> 這兩個套件在 PyPI 上「看起來」是二進位取得方案，實則是陷阱。
> **判斷依據必須是 wheel 內容，不是套件名稱或 README 描述。**

---

## 四、原生函式庫型（內含 .dll / .pyd，但沒有 CLI）

| 套件 | 版本 | 二進位數 | 用途 | 能否取代 ffmpeg CLI |
|---|---|---|---|---|
| **`av`（PyAV）** | 19.0.2 | **73** | **內含 FFmpeg libav* 函式庫** | ❌ 沒有 ffmpeg 指令，但可用 Python 直接呼叫 libav 做編解碼 |
| `msvc-runtime` | 14.44.35112 | 23 | Windows VC++ 執行階段庫 | — |
| `numpy` | 2.5.4 | 21 | 數值運算 | — |
| `pymupdf` | 2.0 | 5 | MuPDF（PDF 解析/渲染） | — |
| `opencv-python-headless` | 5.0.0.93 | 2 | OpenCV（無 GUI 依賴） | — |
| `curl_cffi` | 0.16.3 | 2 | libcurl-ffi（含 TLS 指紋偽裝） | — |
| `duckdb` | 2.0.0 | 1 | DuckDB 引擎 | — |
| `python-magic-bin` | 0.4.14 | 1 | libmagic（檔案型態辨識） | — |
| `pikepdf` | — | 3 | qpdf 綁定 | — |

> **`av`（PyAV）是 ffmpeg CLI 不可得時的重要替代**：wheel 內含完整 FFmpeg 函式庫
> （libavcodec / libavformat / libavfilter …），可用 Python API 做到編解碼、縮圖、串流，
> 完全不需要外部 ffmpeg 執行檔。缺的是「命令列工具介面」與部分硬體編碼器。

---

## 五、本機既有的 ffmpeg 副本（實測搜尋結果）

`Get-ChildItem -Recurse -Include ffmpeg.exe` 掃 `C:\Users\<USER>`、`D:\Downloads`、`D:\80-Opnecode` 的結果：

| 路徑 | 大小 | 版本 | 可用性 |
|---|---|---|---|
| `C:\Users\<USER>\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe` | 98.1 MB | **9.0.1**（gcc 16.1.0） | ✅ **已放進使用者層 PATH** |
| `C:\Users\<USER>\.local\ffmpeg\bin\ffmpeg.exe` | 83.6 MB | 7.1（PyPI wheel） | ✅ 備援（路徑已自 PATH 移除） |
| `C:\Users\<USER>\.local\ffmpeg\node_modules\@ffmpeg-installer\win32-x64\ffmpeg.exe` | 61.5 MB | **4.1**（2018） | ❌ 太舊，不支援 `-fps_mode` |
| `C:\Users\<USER>\AppData\Local\vibe\ffmpeg.exe` | 94.7 MB | — | 第三方工具內附 |
| `C:\Users\<USER>\AppData\Roaming\TRAE SOLO\...\tools\app\ffmpeg\ffmpeg.exe` | 213 MB | — | 第三方工具內附 |
| `D:\80-Opnecode\Workspace\_maidate_work\ffmpeg_pkg\ffmpeg-9.0-essentials_build\bin\ffmpeg.exe` | 98 MB | 9.0 | ✅ 舊工作區副本 |
| `D:\80-Opnecode\Tools\webui\ffmpeg.exe` | 216.4 MB | — | 第三方工具內附 |
| `D:\Downloads\Tools\kdenlive-25.08.0_standalone\bin\ffmpeg.exe` | 0.4 MB | — | ⚠️ 僅 0.4 MB，是 launcher stub |
| `D:\Downloads\Tools\KMPlayerPortable_...\LAVFilters64\ffmpeg.exe` | 43 MB | — | 舊解碼器 |
| `D:\Downloads\2025全年...\YoutubeDownloader.win-x64\ffmpeg.exe` | 55.5 MB | — | 第三方內附 |

### 已修正的失效紀錄

`video-analysis` skill 原本記錄的兩個路徑 **已不存在**：

| 舊紀錄（失效） | 現況 |
|---|---|
| `C:\Users\<USER>\opencode-tools\ffmpeg.exe` | ❌ 整個 `opencode-tools` 目錄不存在 |
| `D:\Downloads\2026-08-10-video2text\_maidate_work\ffmpeg_pkg\ffmpeg-9.0-essentials_build\bin\ffmpeg.exe` | ❌ `D:\Downloads\2026-08-10-video2text` 不存在 |

→ 已改為指向 `C:\Users\<USER>\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\`（實測存在）。

### 9.0.1 vs 7.1 能力對照（實測）

| 項目 | 9.0.1（gyan.dev essentials） | 7.1（PyPI wheel） |
|---|---|---|
| encoders | **126** | 125 |
| decoders | **294** | 289 |
| libx264 / libx265 / libaom-av1 | ✅ | ✅ |
| nvenc / h264_nvenc / hevc_nvenc | ✅ | ✅ |
| libsvtav1 | ❌ | ❌ |
| 取得成本 | **零（本機既有）** | 需 pip 從 PyPI 拉 31 MB wheel |
| 可重現性 | 依賴本機磁碟 | ✅ 版本固定 |
| `-fps_mode`（CDP 錄影必要） | ✅ | ✅ |

→ 兩者都能用；**9.0.1 更新且零下載**，故採 9.0.1 為 PATH 主項、7.1 留備援。

---

## 六、已知「無可靠 PyPI 管道」的工具

| 工具 | 情況 | 替代 |
|---|---|---|
| poppler（`pdftoppm`） | PyPI 無內含二進位的官方套件 | 用 `pymupdf` 取代（已可 pip 取得） |
| tesseract OCR | `pytesseract` 只是 wrapper | `rapidocr-onnxruntime`（內含 ONNX 模型） |
| ImageMagick | 同上 | Pillow / `pymupdf` |
| whisper 模型 | 模型需從 HF 下載 | `cdn-lfs.huggingface.co` 被封 → 需申請放行 |
| Chromium / Playwright 瀏覽器 | 需 `playwright install` 下載 | 被封；但本機已有 Edge 153 可直接用 CDP |
| Node 直譯器 | nodejs.org 被封 | nvm + npmmirror 鏡像 ✅ |

---

## 七、資料來源與重現方式

| 資料 | 取得方式 |
|---|---|
| wheel 清點 | `pip download --no-deps --only-binary :all:` + `zipfile` 讀取內容 |
| 執行期下載來源 | 掃描 wheel 內 `.py` 的 `http(s)://` 字串並過濾下載型網域 |
| 本機 ffmpeg 副本 | `Get-ChildItem -Recurse -Include ffmpeg.exe`（4 個根目錄） |
| 網域可達性 | `curl.exe -s -o NUL -w "%{http_code}" -x $env:HTTPS_PROXY --max-time 15` |
| uv 行為 | `uv tool install ruff`（成功）、`uv python install 3.13`（失敗，錯誤訊息已記錄） |
| yt-dlp 行為 | `pip install --target` 後 `python -m yt_dlp --version` → 2026.10.21 |
| playwright node.exe | `playwright/driver/node.exe --version` → v24.21.0 |

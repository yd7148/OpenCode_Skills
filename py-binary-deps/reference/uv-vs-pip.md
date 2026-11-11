# uv 與 pip 功能重疊與差異（本機實測）

> 實測日期：2026-10-22 ｜ Windows x64、Python 3.13.12、公司代理
> uv 0.13.5（`C:\Users\<USER>\.local\uv\bin\uv.exe`）
> 所有數據皆為本機實跑，非引用第三方評測。

---

## 一、一句話結論

**兩者高度重疊但不等價**：

- **`uv pip install` 是 `pip install` 的直接取代品**（同語法、同 PyPI、同 venv、**相依樹完整**）
- **uv 多出的是「專案管理層」與「工具管理層」**：跨平台 lockfile、`uv tool`/`uvx`、直譯器管理、環境精確同步
- **pip 多出的是「成熟度與相容性保證」**：十餘年的第三方相容性、更多邊緣選項、企業私有 index 的複雜認證
- **本機的關鍵差異**：uv 的 rustls **不信任公司 MITM CA** → 非 PyPI 的 HTTPS 會失敗；且 `uv python install` 走 GitHub releases → **本機不可用**

> 老師那句「uv 比 pip 快、也好管理、更有效率」**方向正確**，但精確版是：
> **速度**（實測 2.9–12.2 倍）與**專案工作流**（lockfile / tool 管理）確實強；
> **但 pip 的相容性與邊緣選項覆蓋率仍是 uv 追不上的**，而本機的封鎖環境讓 uv 的某些能力直接失效。

---

## 二、功能重疊地圖

| 能力 | pip | uv | 重疊程度 |
|---|---|---|---|
| 從 PyPI 安裝套件 | `pip install <pkg>` | `uv pip install <pkg>` | ✅ **完全重疊**（uv 更快） |
| 從 requirements 檔安裝 | `pip install -r req.txt` | `uv pip install -r req.txt` | ✅ **完全重疊**（實測相依樹相同） |
| 建立虛擬環境 | `python -m venv` | `uv venv` | ✅ 重疊（實測 12.2 倍快） |
| 列出已裝套件 | `pip list` / `pip freeze` | `uv pip list` / `uv pip freeze` | ✅ 完全重疊 |
| 升級套件 | `pip install -U` | `uv pip install -U` | ✅ 完全重疊 |
| 卸載套件 | `pip uninstall` | `uv pip uninstall` | ✅ 完全重疊 |
| 產生釘選需求檔 | `pip freeze > req.txt`（手動） | `uv pip compile pyproject.toml`（自動，含 hash） | 🔺 uv 明顯較強 |
| **跨平台 lockfile** | ❌ 無 | ✅ **`uv.lock`**（含 hash、全平台一致） | ❌ **uv 獨有** |
| **專案初始化** | ❌ 手動寫 pyproject | ✅ `uv init` | ❌ uv 獨有 |
| **專案相依宣告** | 手動編輯 | ✅ `uv add` / `uv remove` | ❌ uv 獨有 |
| **CLI 工具隔離安裝** | 需 pipx | ✅ `uv tool install`（內建） | ❌ uv 獨有 |
| **免安裝直接跑工具** | 需 pipx run | ✅ `uvx <tool>` | ❌ uv 獨有 |
| **環境精確同步** | `pip install -r`（近似） | ✅ `uv pip sync`（**但有陷阱，見下**） | 🔺 uv 較強但有條件 |
| **直譯器版本管理** | ❌ | ✅ `uv python install` | ❌ uv 獨有，**但本機被封鎖不可用** |
| **零 Python 依賴的單檔執行檔** | ❌ 需 Python | ✅ `uv.exe`（Rust 單檔） | ❌ uv 獨有 |
| sdist 需自行編譯 | ✅ | ✅ | 重疊（uv 亦需 toolchain） |
| 企業私有 index 複雜認證 | ✅ 設定項多 | ⚠️ 支援但覆蓋較少 | pip 較強 |
| `pip download` / `pip wheel` | ✅ | ⚠️ 部分覆蓋 | pip 較強 |
| 第三方相容性保證 | ✅ 十餘年 | ⚠️ 較新，偶有 edge case | pip 較強 |

---

## 三、本機實測 benchmark

### 3.1 速度（實跑，非引用）

| 項目 | pip | 時間 | uv | 時間 | 倍數 |
|---|---|---|---|---|---|
| 建立 venv | `python -m venv` | **7.51s** | `uv venv` | **0.62s** | **12.2×** |
| 安裝 numpy（冷快取，binary wheel ~17 MB） | `pip install` | **11.51s** | `uv pip install` | **3.99s** | **2.9×** |
| 安裝 numpy（熱快取，新 venv） | `pip install --no-cache-dir` | **15.38s** | `uv pip install`（全域快取命中） | **1.51s** | **10.2×** |
| 安裝 requests（純 Python） | `pip install` | **4.76s** | `uv pip install` | **1.20s** | **4.0×** |
| 建立專案 + 鎖檔 | ❌ 無此流程 | — | `uv init` + `uv add` | **1.35s + 0.68s** | uv 獨有 |
| 安裝 CLI 工具 | 需 pipx（未安裝） | — | `uv tool install ruff` | **1.94s** | uv 獨有 |
| 免安裝執行工具 | 需 pipx run | — | `uv tool run ruff` | **1.16s** | uv 獨有 |

**為什麼快**：
1. **Rust 實作 + 平行下載解壓**，不靠 CPython 解壓器
2. **全域共享快取**（`%LOCALAPPDATA%\uv\cache`）→ 第二次安裝近乎「複製檔案」
3. **硬連結**（hardlink）到 venv → 同一份檔案只佔一份磁碟
4. **零啟動成本**：`uv` 是單檔 Rust 執行檔，不需要先啟動 Python 再載入 pip

> **注意 pip 的 15.38s 是我加了 `--no-cache-dir` 的刻意最壞情況**。
> pip 預設有 HTTP 快取（`%LOCALAPPDATA%\pip\Cache`），但**不快取解壓後的安裝結果**，
> 每次仍要重新解壓 + 寫檔；uv 的快取連解壓結果都保留。

### 3.2 產出品質差異

| 面向 | pip | uv |
|---|---|---|
| 釘選檔 | `pip freeze` 手動產生、**無 hash** | `uv pip compile` 自動產生、**含 sha256 hash**（可驗證完整性） |
| 鎖檔 | ❌ 無跨平台 lockfile | ✅ `uv.lock`（含所有平台解析結果、hash、版本） |
| 環境復現 | `pip install -r`（版本可能漂移） | `uv sync`（依 `uv.lock` 精確還原） |

---

## 四、實測到的陷阱（重要）

### 陷阱 1：`uv pip sync` 搭配寬鬆 requirements 檔會**遺漏相依套件**

實測（乾淨 venv，requirements.txt 只有一行 `requests`）：

```
$ uv pip sync requirements.txt --python <venv>
Resolved 1 package in 4ms
Installed 1 package in 31ms
$ python -c "import requests"
ModuleNotFoundError: No module named 'urllib3'   ← urllib3 沒被裝
```

對照 pip：

```
$ pip install -r requirements.txt
$ python -c "import requests"
requests 2.34.2 OK                                 ← 完整相依樹
```

**規則**：`uv pip sync` 設計給**完全釘選**的來源檔使用。
寬鬆的 `requirements.txt` 會被當成「完整清單」→ 只裝列出的套件 → 相依遺漏。
正確做法：

```powershell
# 先產生完整釘選檔（含相依 + hash），再 sync
uv pip compile pyproject.toml --output-file requirements.lock.txt
uv pip sync requirements.lock.txt --python <venv>
```

實測 `uv pip compile` 產生的釘選檔 → `uv pip sync` → `requests 2.34.2 / urllib3 2.8.0` ✅

| 指令 | 寬鬆 requirements | 完全釘選 requirements |
|---|---|---|
| `pip install -r` | ✅ 完整相依 | ✅ 完整相依 |
| `uv pip install -r` | ✅ 完整相依 | ✅ 完整相依 |
| **`uv pip sync`** | ❌ **只裝列出的套件** | ✅ 完整相依 |

### 陷阱 2：`uv pip sync` 不接受 `uv.lock`

```
$ uv pip sync uv.lock
error: Couldn't parse requirement in uv.lock at position 0
  cause: no such comparison operator "=", must be one of ~= == != <= >= < > ===
```

`uv.lock` 要用**專案層級的 `uv sync`** 消費，不是 `uv pip sync`。

### 陷阱 3：`uv pip sync` 必須指定來源檔

```
$ uv pip sync --project <dir> --python <venv>
error: the following required arguments were not provided: <SRC_FILE>...
```

### 陷阱 4：`uv pip sync` 是**破壞性**的

它會把環境**精確對齊**來源檔 —— 來源檔沒列的套件會被移除。
在共用環境或手動裝過東西的 venv 上執行要特別小心（實測："Uninstalled 1 package"）。

---

## 五、pip 仍然比較強的地方

| 面向 | 說明 |
|---|---|
| **相容性保證** | pip 是 Python 官方的安裝工具，第三方套件以 pip 為基準測試十餘年；uv 較新，偶有邊緣案例（尤其舊套件 + 老 Python + 複雜 build） |
| **企業私有 index** | 多個 index、keyring、`--trusted-host`、憑證釘選等細項，pip 的設定項遠多於 uv |
| **邊緣子命令** | `pip download`、`pip wheel`、`pip cache`、`pip inspect`、`pip check`、`pip debug` 等，uv 覆蓋率較低 |
| **非 wheel 套件流程** | 需自行編譯的 sdist、需要系統函式庫的套件，pip 的錯誤訊息與排障文件更成熟 |
| **既有 CI / script 相容性** | 本機現有 skill 大量使用 `py -3 -m pip install ...`，一次全換成 uv 有風險 |

---

## 六、本機的特殊限制（uv 在這台機器上不是全功能）

| 限制 | 原因 | 影響 | 替代 |
|---|---|---|---|
| **`uv python install` 不可用** | 需 `github.com/astral-sh/python-build-standalone/releases/...` → 被公司代理封鎖 | 無法用 uv 裝 Python 直譯器 | 用既有的 `py -3`（3.13.12）或 nvm + npmmirror 裝 Node |
| **非 PyPI 的 HTTPS 會失敗** | uv 用 rustls + webpki 根憑證，**不讀 Windows 憑證存放區** → 不信任公司 MITM CA | 報 `invalid peer certificate: UnknownIssuer` | pip / Node / curl / git 用 Windows 憑證 → 信任公司 CA |
| `uv tool install` 的套件若需額外下載 | 同上 | 僅影響套件自身不在 wheel 內的情況 | 優先選 wheel 內含二進位的套件 |

> **對照**：同一個網域，**pip 行、uv 不行**是正常現象 —— 這是 TLS 信任根差異，不是網路問題。

---

## 七、建議的分工與遷移路線

### 7.1 現階段（保守，已驗證可用）

| 場景 | 用什麼 | 理由 |
|---|---|---|
| 既有 skill 的 `py -3 -m pip install ...` | **維持 pip** | 已驗證可用，改動風險不划算 |
| 一次性裝個工具、想乾淨 | `uvx <tool>` | 免安裝、1.16s |
| 裝 CLI 工具（ruff 等） | `uv tool install <tool>` | 內建隔離環境，取代 pipx |
| 新專案、需要 lockfile | `uv init` + `uv add` + `uv sync` | 跨平台可重現 |
| 純粹「快一點」地裝套件 | `uv pip install -r req.txt` | 相依樹與 pip 等價（實測確認） |
| **需要非 PyPI 來源的套件** | **pip** | uv 不信任公司 CA |

### 7.2 遷移路線（若要全面轉 uv）

1. 先用 `uv pip install -r` 取代 `pip install -r`（相依樹等價，已驗證）
2. 再把 `python -m venv` 換成 `uv venv`（12.2× 快）
3. 新專案一律 `uv init` + `uv add`，讓 `uv.lock` 成為唯一事實來源
4. **千萬不要**把 `uv pip sync` 指向寬鬆的 requirements.txt（陷阱 1）
5. 保留 pip 作為逃生門（企業 index、怪異 sdist、CI 相容性）

---

## 八、常用指令速查（本機路徑）

```powershell
$UV = "$env:USERPROFILE\.local\uv\bin\uv.exe"     # 全域已安裝並在 PATH

uv --version                    # 0.13.5
uv python find                  # 找本機可用的 Python（→ Python313\python.exe）
uv venv .venv                   # 建立 venv（0.62s）
uv pip install requests         # 安裝（相當於 pip install）
uv pip install -r req.txt       # 安裝（相依樹與 pip 等價）
uv pip compile pyproject.toml --output-file req.lock.txt   # 產生釘選+hash 檔
uv pip sync req.lock.txt        # 精確同步（僅用於完全釘選檔）
uv init --name demo             # 初始化專案（含 pyproject.toml）
uv add requests                 # 宣告相依（自動更新 uv.lock）
uv sync                         # 依 uv.lock 還原環境
uv tool install ruff            # 隔離安裝 CLI 工具（取代 pipx）
uv tool list                    # 列出已裝工具
uv tool update --all            # 一次更新全部工具
uvx ruff --version              # 免安裝直接執行
uv cache dir                    # 快取位置
uv cache clean                  # 清快取
```

---

## 九、實測資料來源

| 資料 | 方式 |
|---|---|
| benchmark | `node bench-pip-vs-uv.cjs`（每項獨立計時，uv 使用獨立 `UV_CACHE_DIR` 模擬冷啟動） |
| 相依樹比對 | 乾淨 venv 各自安裝後 `python -c "import requests, urllib3"` |
| `uv pip sync` 陷阱 | 三種來源檔（寬鬆 requirements / 釘選 requirements / uv.lock）各跑一次比對 |
| 版本 | `uv --version` → 0.13.5 (46776a95d 2026-10-21 x86_64-pc-windows-msvc) |

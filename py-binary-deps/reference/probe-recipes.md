# 探測與安裝腳本（可直接執行）

> 全部以本機實測過的路徑撰寫。PowerShell 5.1 注意：**不要用 `Set-Content -Encoding UTF8`**
> 改含中文的檔案（會寫入 BOM）；用編輯工具或 Node `fs.writeFileSync(p, s, 'utf8')`。

---

## 一、網域可達性探測（永遠第一步）

```powershell
function Test-Channel([string]$Url) {
  $code = curl.exe -s -o NUL -w "%{http_code}" -x $env:HTTPS_PROXY --max-time 15 $Url 2>&1
  $verdict = switch -Regex ($code) {
    '^000$' { '封鎖' } '^(401|403)$' { '通(來源端拒絕匿名)' } '^[23][0-9][0-9]$' { '通' } default { "未知($code)" }
  }
  "{0,-8} {1,-28} {2}" -f $code, $verdict, $Url
}

# 本機已知的關鍵網域
foreach ($u in @(
  'https://pypi.org/simple/',
  'https://files.pythonhosted.org/',
  'https://registry.npmjs.org/',
  'https://cdn.npmmirror.com/binaries/node/',
  'https://github.com/',
  'https://raw.githubusercontent.com/',
  'https://codeload.github.com/',
  'https://objects.githubusercontent.com/',
  'https://release-assets.githubusercontent.com/',
  'https://ffmpeg.org/',
  'https://www.gyan.dev/ffmpeg/builds/',
  'https://nodejs.org/dist/index.json'
)) { Test-Channel $u }
```

**判讀**：`000` = 封鎖；`401`/`403` = **通**（僅來源端拒絕匿名存取，不是網路問題）。

---

## 二、本機既有副本搜尋（成本最低，先做）

```powershell
function Find-Existing([string[]]$Names, [string[]]$Roots = @(
  "$env:USERPROFILE", 'D:\Downloads', 'D:\80-Opnecode', 'D:\01-工作資料夾')) {
  foreach ($r in $Roots) {
    if (-not (Test-Path $r)) { continue }
    Get-ChildItem -Path $r -Recurse -Include $Names -File -ErrorAction SilentlyContinue -Force |
      Select-Object @{n='MB';e={[math]::Round($_.Length/1MB,1)}},
                    LastWriteTime,
                    @{n='Path';e={$_.FullName}}
  }
}

Find-Existing @('ffmpeg.exe','ffprobe.exe') | Sort-Object Path | Format-Table -AutoSize
```

**驗版本**（不要只看檔名）：

```powershell
& 'C:\Users\<USER>\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe' -version | Select-Object -First 1
```

**判斷是否為 launcher stub**（某些工具只放 0.4 MB 的啟動器）：

```powershell
Get-ChildItem -Recurse -Filter ffmpeg.exe -File | Where-Object { $_.Length -lt 5MB } | Select-Object FullName, Length
```

---

## 三、wheel 內容盤查（判斷「內含」vs「執行期下載」）

存成 `probe-wheel.cjs`（Node，可用 `node` 直接跑）：

```javascript
const { execSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const PY = "C:\\Users\\<USER>\\AppData\\Local\\Programs\\Python\\Python313\\python.exe";
const TMP = "C:\\Users\\<USER>\\AppData\\Local\\Temp\\opencode\\wheelprobe";
fs.mkdirSync(TMP, { recursive: true });

const pkgs = process.argv.slice(2);
if (!pkgs.length) { console.error("用法: node probe-wheel.cjs <套件名> [...]"); process.exit(1); }

function sh(cmd) {
  try { return execSync(cmd, { encoding: "utf8", stdio: ["ignore","pipe","pipe"], timeout: 240000 }); }
  catch (e) { return "ERR:" + ((e.stdout||"") + (e.stderr||"")); }
}

for (const p of pkgs) {
  const dir = path.join(TMP, p.replace(/[^a-zA-Z0-9]/g, "_"));
  fs.mkdirSync(dir, { recursive: true });
  sh(`"${PY}" -m pip download --no-deps --only-binary :all: -d "${dir}" "${p}" 2>&1`);
  const whl = fs.readdirSync(dir).find((f) => f.endsWith(".whl"));
  if (!whl) { console.log(`${p.padEnd(22)} 下載失敗或無 wheel`); continue; }

  const probe = sh(
    `"${PY}" -c "import zipfile,sys,json,re;` +
    `z=zipfile.ZipFile(sys.argv[1]);n=z.namelist();` +
    `exe=[x for x in n if x.lower().endswith(('.exe','.so','.dylib'))];` +
    `dll=[x for x in n if x.lower().endswith(('.dll','.pyd'))];` +
    `u=set();` +
    `[u.update(re.findall(r'https?://[a-zA-Z0-9./_-]{6,80}', z.read(x).decode('utf8','ignore'))) for x in n if x.endswith('.py')];` +
    `dl=[x for x in u if any(k in x.lower() for k in ('github.com/','gyan.dev','/releases/download','raw.githubusercontent'))];` +
    `print(json.dumps({'exe':len(exe),'s':exe[:3],'dll':len(dll),'dl':dl[:3]}))" "${path.join(dir, whl)}"`
  );
  let i = null;
  try { i = JSON.parse(probe.split("\n").filter((l) => l.trim().startsWith("{")).pop()); } catch {}
  const kind = i?.exe > 0 ? "★含可執行檔" : i?.dll > 0 ? "僅原生函式庫" : "純 Python";
  console.log(`${p.padEnd(22)} ${kind.padEnd(14)} exe=${i?.exe ?? "?"} dll=${i?.dll ?? "?"} ${(i?.s || []).join(", ")}`);
  if (i?.dl?.length) console.log(`${"".padEnd(22)}   ⚠ 執行期下載: ${i.dl.join(" | ")}`);
}
```

執行：

```powershell
node probe-wheel.cjs imageio-ffmpeg yt-dlp static-ffmpeg ffmpeg-downloader uv ruff aria2 av
```

**判讀**：
- `★含可執行檔` → 直接 pip 安裝即可用 ✅
- `純 Python` → pip 安裝即可用 ✅（CLI 以 `python -m <pkg>` 呼叫）
- `⚠ 執行期下載` → **本機不可用** ❌

---

## 四、安裝與驗證

### 4.1 純 Python 工具（yt-dlp 等）

```powershell
py -3 -m pip install --user yt-dlp
py -3 -m yt_dlp --version          # 2026.10.21
```

需要獨立執行檔時可自製 wrapper（避免下載被封的 `.exe`）：

```powershell
$shim = "$env:USERPROFILE\bin\yt-dlp.cmd"
New-Item -ItemType Directory -Force -Path (Split-Path $shim) | Out-Null
Set-Content -Path $shim -Encoding ASCII -Value '@echo off`r`npy -3 -m yt_dlp %*'
```

### 4.2 wheel 內含可執行檔（ffmpeg / uv / ruff / aria2）

```powershell
# 方式 A：裝進專用目錄後自行加入 PATH
py -3 -m pip install --target "$env:USERPROFILE\.local\ffmpeg-py" --no-cache-dir imageio-ffmpeg
Copy-Item "$env:USERPROFILE\.local\ffmpeg-py\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe" `
          "$env:USERPROFILE\.local\ffmpeg\bin\ffmpeg.exe" -Force

# 方式 B：用 uv（自動處理環境與 PATH）
py -3 -m pip install --user uv
uv tool install ruff
uvx ruff --version
```

> **佈局陷阱**：`pip install --target <dir>` 時，wheel 的 console script 會落在
> **`<dir>\bin\<name>.exe`**；一般 `pip install`（site-packages）則落在
> `<site-packages>\<pkg>.data\scripts\<name>.exe`。寫自動化腳本時不要硬編碼路徑，先列出實際檔案。

### 4.3 加入使用者層 PATH（永久生效，不影響既有行程）

```powershell
$dir = 'C:\Users\<USER>\ffmpeg\ffmpeg-9.0.1-essentials_build\bin'
$userPath = [Environment]::GetEnvironmentVariable('Path','User')
$parts = $userPath -split ';' | Where-Object { $_ -ne '' -and $_ -ne $dir }
[Environment]::SetEnvironmentVariable('Path', (($parts + $dir) -join ';'), 'User')
```

> ⚠️ **PATH 變更對既有長駐程序無效**（程序啟動時繼承環境快照）。
> 例：`browser-control` 的 relay → 必須 `browser-control relay restart` 才會套用。
> 新的互動式 shell 與新開的 OpenCode session 則會直接繼承新的使用者層 PATH。

### 4.4 必須立即驗證

```powershell
ffmpeg -version | Select-Object -First 1        # 確認解析到的是預期版本
ffprobe -version | Select-Object -First 1
(Get-Command ffmpeg).Source                     # 確認實際路徑
```

---

## 五、已知會失敗的指令與替代

| 指令 | 失敗原因 | 替代 |
|---|---|---|
| `nvm install 22.x`（直連） | `nodejs.org` 被封 | `NVM_NODEJS_ORG_MIRROR=https://cdn.npmmirror.com/binaries/node` |
| `winget install <官方來源套件>` | winget 只掛 `msstore` 來源 | `winget source add -n winget -a https://cdn.winget.microsoft.com/cache/source2.msix -t Microsoft.Restricted`（需管理員） |
| `uv python install 3.13` | 需 GitHub releases；且 rustls 不信任公司 CA | 用既有直譯器：`uv tool install --python 3.13 <pkg>` |
| `pip install static-ffmpeg` / `ffmpeg-downloader` | 執行期下載來源被封 | `pip install imageio-ffmpeg` |
| `pip install ffmpeg-static` | postinstall 下載被封 + Node 不信任公司 CA | 同上 |
| `playwright install chromium` | 瀏覽器下載被封 | 用本機既有 Edge/Chrome + CDP |
| `git clone https://github.com/x/y.git`（淺 clone 大 repo） | 走 `objects.githubusercontent.com` 被打 | `codeload.github.com` 取 tarball/zip |
| `curl --noproxy "*"` 直連 | 沒有對外直連路徑 | 一律走代理 |

---

## 六、Node / Python 的 TLS 差異（本機實測）

| 工具 | 憑證來源 | 對公司 MITM CA | 非 PyPI 的 HTTPS |
|---|---|---|---|
| pip / Node / curl / git | **Windows 憑證存放區** | ✅ 信任 | ✅ 可用 |
| **uv（rustls + webpki）** | 內建根憑證 | ❌ 不信任 | ❌ `invalid peer certificate: UnknownIssuer` |

→ 判讀連線失敗時，**先確認是「網域被封」還是「憑證不信任」**：
`000` 通常是被封；TLS 錯誤則是憑證問題，換工具（pip 取代 uv）即可。

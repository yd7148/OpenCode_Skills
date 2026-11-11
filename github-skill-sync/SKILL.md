---
name: github-skill-sync
description: 同步本機 OpenCode skills（`~/.config/opencode/skills/`）與 GitHub 上的 `yd7148/OpenCode_skill` 收藏庫。本 skill 同時管理**下載（GitHub→本機）**與**上傳（本機→GitHub）**兩個方向，並維持兩邊說明文件（README.md / SKILLS.md）一致。涵蓋無 Git／無 gh 的 Windows 機器如何用 MinGit 可攜版與 GitHub Device Flow 完成授權與推送。Use when asked to "同步 skill", "更新 skill 收藏庫", "sync skills", "上傳本機 skill 到 GitHub", "從 GitHub 拉下 skills", "git 沒安裝", "push 到 GitHub", or to keep local skills in sync with the OpenCode_skill repo.
license: MIT
compatibility: opencode
metadata:
  audience: opencode agents
  workflow: opencode-skill-sync
  languages: zh-TW
---

# github-skill-sync — 本機 ↔ GitHub Skills 同步

同步本機 OpenCode skills 目錄與 GitHub 上的 `yd7148/OpenCode_skill` 收藏庫。管理
**下載（GitHub→本機）** 與 **上傳（本機→GitHub）** 兩個方向，並維持兩邊說明文件一致。

## 路徑一律在執行時解析，不要寫死

本 skill 曾把某台機器上的絕對路徑寫在文件裡，導致在其他機器上照抄就失敗。
**所有路徑都必須在執行時解析**，使用者名稱與磁碟機都可能不同。

```powershell
# 本機 skills 目錄（canonical；所有 OpenCode 平台一致）
$SKILLS = Join-Path $env:USERPROFILE ".config\opencode\skills"

# GitHub repo 本機 clone；不存在就 clone
$CLONE = Join-Path $env:USERPROFILE "OpenCode_skill"
$REMOTE = "https://github.com/yd7148/OpenCode_skill.git"
```

> 不要假設 skills 在 `<PROJECT_ROOT_A>\.opencode\skills\`、`<PROJECT_ROOT_C>\...` 或任何
> 使用者名稱特定的目錄。先用 `Join-Path $env:USERPROFILE` 推導，再確認目錄存在。

### 本機實際佈局（2026-11-10 實測）

這台機器有**兩個** Git repo，角色不同，不要搞混：

| 角色 | 本機路徑 | 遠端 | 狀態 |
|---|---|---|---|
| **本機 skills 原始碼**（工作區） | `D:\OpenCode-Project\01-Skills\` | `yd7148/OpenCode_skill-local.git` | ⚠️ 遠端 **404 不存在**，只能本機 commit，無法 push |
| **上游收藏庫**（發布用） | `D:\OpenCode-Project\01-Skills\OpenCode_skill\` | `yd7148/OpenCode_skill.git` | ✅ 存在且可 push（**private**） |

- `01-Skills\` 內的每個 `<skill>/SKILL.md` 是**編輯來源**。
- `01-Skills\OpenCode_skill\` 是上游 clone，**改完 skill 後要同步過去再 push**，
  否則 GitHub 上的收藏庫看不到更新。
- `01-Skills\OpenCode_skill\` 是巢狀 clone，**必須排除**在 `01-Skills` 的版控之外
  （否則 `git add -A` 會把整個上游 repo 當成一般檔案塞進去）。

## 環境準備：沒有 Git、沒有 gh 也能推

很多 Windows 機器 `git` 不在 PATH、沒有 SSH key、`cmdkey` 裡也沒有 GitHub 憑證。
**不要假設 `git` 或 `gh` 已安裝**，先偵測再決定要不要走可攜版流程。

### 0.1 偵測

```powershell
Get-Command git -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
Get-Command gh  -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
```

### 0.2 沒有 git → 裝 MinGit 可攜版（解壓即用，不污染系統）

```powershell
$dst = "$env:LOCALAPPDATA\Temp\opencode\mingit"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" `
        -Headers @{ "User-Agent" = "opencode" } -TimeoutSec 60
$asset = $rel.assets | Where-Object { $_.name -match 'MinGit-.*-64-bit\.zip$' } | Select-Object -First 1
Invoke-WebRequest -Uri $asset.browser_download_url `
        -OutFile "$env:LOCALAPPDATA\Temp\opencode\MinGit.zip" -UseBasicParsing -TimeoutSec 600
Expand-Archive -Path "$env:LOCALAPPDATA\Temp\opencode\MinGit.zip" -DestinationPath $dst -Force
$env:PATH = "$dst\cmd;$env:PATH"      # 每個 session 都要重設 PATH
git --version
```

> MinGit 比 PortableGit 小（~38 MB vs ~60 MB）且解壓即用，不需要自我解壓 exe。
> 版本實測：2.56.0.4（`v2.56.0.windows.4`）。

### 0.3 沒有 gh → 裝 GitHub CLI 可攜版

```powershell
$dst = "$env:LOCALAPPDATA\Temp\opencode\gh"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/cli/cli/releases/latest" `
        -Headers @{ "User-Agent" = "opencode" } -TimeoutSec 60
$asset = $rel.assets | Where-Object { $_.name -match 'windows_amd64\.zip$' } | Select-Object -First 1
Invoke-WebRequest -Uri $asset.browser_download_url `
        -OutFile "$env:LOCALAPPDATA\Temp\opencode\gh.zip" -UseBasicParsing -TimeoutSec 600
Expand-Archive -Path "$env:LOCALAPPDATA\Temp\opencode\gh.zip" -DestinationPath $dst -Force
$env:PATH = "$dst\bin;$env:PATH"
gh --version
```

### 0.4 授權：GitHub Device Flow（不用打密碼、不用 SSH）

```powershell
$env:PATH = "$env:LOCALAPPDATA\Temp\opencode\mingit\cmd;$env:LOCALAPPDATA\Temp\opencode\gh\bin;$env:PATH"

# 裝置碼授權；gh 會把 code 複製到剪貼簿並印出 https://github.com/login/device
gh auth login --web --hostname github.com --git-protocol https

# 讓 git 改用 gh 取用 token（否則 repo 內的 credential.helper=manager 找不到憑證）
gh auth setup-git

gh auth status        # 應顯示 "✓ Logged in to github.com account <user>"
```

> ⚠️ `gh auth setup-git` **需要 `git` 在 PATH**，否則報
> `failed to set up git credential helper: unable to find git executable in PATH`。
> 先設好 `$env:PATH` 再執行。
>
> ⚠️ `gh auth login --web` 需要一次人工點擊（貼上 code → Authorize）。
> 若非互動式 shell，可先 `Start-Process chrome https://github.com/login/device` 讓使用者完成。
> 內建 browser 工具（opencode app 內）若未登入 GitHub 就無法自動完成，**不要**在那裡空轉。
>
> token 存於 **Windows 憑證管理員**，不會寫進 repo 的 `.git/config` 或 `.git-credentials`。

### 0.5 沒有 git 也能用 GCM 的裝置碼流程（替代方案）

MinGit 內附 `git-credential-manager.exe`（`ucrt64\bin`），可直接走 GCM 的 GitHub 流程：

```powershell
$env:PATH = "$env:LOCALAPPDATA\Temp\opencode\mingit\ucrt64\bin;$env:PATH"
git-credential-manager github login --device --username <user>
git-credential-manager github list
```

> 實測：GCM 的 `--device` 在非互動式環境下**不會把 code 印到 stdout**，
> 程序會掛住等不到輸入。改用 `gh auth login --web` 比較可靠（code 會印到 stderr）。

## 通用規則（兩個方向都適用）

- **排除**：`.venv/`、`__pycache__/` 一律不複製，避免虛擬環境與快取混入 repo。

  兩者在 repo 中保留供參考，但同步到本機時必須跳過——下載迴圈已加 `-notlike` 過濾。
  這與「非 skill 目錄」不同：那種是結構性排除（無 `SKILL.md`），這兩種確實是 skill，只是本機不裝。
- **空目錄**：Git 不追蹤空目錄。空的 skill 資料夾（無 `SKILL.md`）不會上傳；上傳前若發現空資料夾要提醒使用者。
- **說明文件一致性**：repo 根目錄的 `README.md` / `SKILLS.md` 更新後，兩邊都應有一份。
- **索引不要手改**：兩份文件的索引區塊由 `scripts/gen_index.py` 產生，改完 skill 後執行
  `python3 scripts/gen_index.py`，並用 `--check` 確認過期狀態。
- **commit 身份**：`git -c user.name="yd7148" -c user.email="<USER_EMAIL>"`。
- **編碼**：skill 內含大量繁中。**不要用 PowerShell 的 `Get-Content` / `Set-Content` 改寫**——
  `Set-Content -Encoding UTF8` 會寫入 BOM，且讀寫可能毀損中文。用編輯工具或 Node
  `fs.writeFileSync(p, s, 'utf8')`。改完後檢查檔案開頭有沒有 BOM。

## 方向一：下載（GitHub → 本機）

把 GitHub 上最新的 skill 內容拉下來，覆蓋到本機使用目錄。

```powershell
$SKILLS = Join-Path $env:USERPROFILE ".config\opencode\skills"
$CLONE  = Join-Path $env:USERPROFILE "OpenCode_skill"

# 1. 更新本機 clone（首次執行時先 git clone）
if (-not (Test-Path $CLONE)) { git clone https://github.com/yd7148/OpenCode_skill.git $CLONE }
else { git -C $CLONE pull origin main }

# 2. 把 repo 中各 skill 同步到本機使用目錄（排除虛擬環境）
Get-ChildItem -LiteralPath $CLONE -Directory -Force |
  Where-Object { $_.Name -ne ".git" -and $_.Name -notlike "comsol*" -and $_.Name -notlike "hcl-*" } |
  ForEach-Object {
  $dest = Join-Path $SKILLS $_.Name
  New-Item -ItemType Directory -Path $dest -Force | Out-Null
  Copy-Item -Path (Join-Path $_.FullName "*") -Destination $dest -Recurse -Force `
    -Exclude ".venv","__pycache__"
}

# 3. 同步根目錄說明文件
Copy-Item "$CLONE\README.md" "$SKILLS\README.md" -Force
Copy-Item "$CLONE\SKILLS.md" "$SKILLS\SKILLS.md" -Force
```

## 方向二：上傳（本機 → GitHub）

把本機新增或修改的 skill 提交並 push 到 GitHub。

```powershell
$SKILLS = Join-Path $env:USERPROFILE ".config\opencode\skills"
$CLONE  = Join-Path $env:USERPROFILE "OpenCode_skill"

# 1. 先確認本機 clone 是最新，避免非 fast-forward 被拒
git -C $CLONE fetch origin
git -C $CLONE pull --rebase origin main

# 2. 把本機 skills 同步進 clone（排除虛擬環境）
Get-ChildItem -LiteralPath $SKILLS -Directory -Force | ForEach-Object {
  $name = $_.Name; $dest = Join-Path $CLONE $name
  if ((Get-ChildItem -LiteralPath $_.FullName -Force | Measure-Object).Count -eq 0) {
    "SKIP 空目錄: $name"; return
  }
  New-Item -ItemType Directory -Path $dest -Force | Out-Null
  Copy-Item -Path (Join-Path $_.FullName "*") -Destination $dest -Recurse -Force `
    -Exclude ".venv","__pycache__"
}

# 3. 更新 repo 根 README.md / SKILLS.md 到 clone（保持說明一致）
Copy-Item "$SKILLS\README.md" "$CLONE\README.md" -Force
Copy-Item "$SKILLS\SKILLS.md" "$CLONE\SKILLS.md" -Force

# 4. 檢視變更、commit、push
git -C $CLONE add -A
git -C $CLONE status --short
git -C $CLONE -c user.name="yd7148" -c user.email="<USER_EMAIL>" commit -m "sync skills"
git -C $CLONE push origin main
```

### 2.1 推送前必做：分清楚「誰的變更」

`git status` 一出現大量 `M` / `D` / `??`，**那些可能不是本次任務產生的**
（例如使用者先前搬移檔案、或另一個工作階段正在同一個 repo 作業）。
**不要 `git add -A` 一把梭**——先逐項確認歸屬，再決定 stage 範圍：

```powershell
git -C $CLONE -c core.quotepath=false status --short --branch
git -C $CLONE diff --stat                       # 看已追蹤檔案改了什麼
git -C $CLONE diff --cached --name-only         # 看已 stage 的範圍
```

分批 stage（教材／文件分兩個 commit）比一次全包更容易回溯與回滾。

### 2.2 推送後必做：雙重驗證

```powershell
git -C $CLONE ls-remote origin main            # 遠端 HEAD
git -C $CLONE rev-parse HEAD                   # 本機 HEAD
git -C $CLONE status --short --branch          # 應為 clean 且與 origin/main 同點
```

兩者 hash 不同就是沒推上去（或推的是別的分支），不要只看 `git push` 的 exit code。

## 方向三：部署全域 AGENTS.md 到其他裝置

skills 同步之外，`~/.config/opencode/AGENTS.md`（全域指令）也需要跨設備一致。
模板放在 repo 的 `opencode-env/`。**先讀 `opencode-env/CROSS-DEPLOY.md` 取完整方案。**

### ⚠️ 先確認 V2 的兩個陷阱

| 陷阱 | 事實 |
|---|---|
| `opencode.jsonc` 的 `instructions` 欄位 | **接受但不載入**（"OpenCode accepts this field but does not load its entries"）。指令一律用 `AGENTS.md` |
| `CLAUDE.md` | **不被支援**（"V2 recognizes AGENTS.md only"） |

另：多個 `AGENTS.md` 是**拼接不是覆蓋**，OpenCode 不做衝突消解 —— 全域與專案層避免同主題重複。

### 分工原則（安全性關鍵）

| 內容 | 放哪 | 理由 |
|---|---|---|
| 跨機器都成立的通用規範 | `opencode-env/AGENTS.md`（進版控） | 可安全公開 |
| 機器專屬（網域清單、代理位址、專案路徑） | `~/.config/opencode/LOCAL-ENVIRONMENT.md`（**不進版控**） | 含內部資訊，會跟著部署外流 |

> 本 repo 是**公開**的。`AGENTS.md` 與 `opencode.jsonc` 內不得出現內部 IP、員工代號、
> 主機名稱、組織網域、憑證。一律用佔位符。

### 部署方式（Windows）

```powershell
$Repo   = Join-Path $env:USERPROFILE "OpenCode_skill"   # 依實際 clone 路徑調整
$Config = Join-Path $env:USERPROFILE ".config\opencode"
New-Item -ItemType Directory -Force -Path $Config | Out-Null

foreach ($f in @("AGENTS.md", "opencode.jsonc")) {
  $src = Join-Path "$Repo\opencode-env" $f
  $dst = Join-Path $Config $f
  if (Test-Path $dst) { Copy-Item $dst "$dst.bak" -Force }   # 先備份
  if ($Link) {
    Remove-Item $dst -Force -ErrorAction SilentlyContinue
    New-Item -ItemType SymbolicLink -Path $dst -Target $src   # 單一來源，自動同步
  } else {
    Copy-Item $src $dst -Force
  }
}
```

**符號連結 vs 複製**：符號連結讓編輯 repo 即生效，不會有兩份內容分歧；
但 repo 搬移或換路徑需重建連結。macOS/Linux 用 `ln -s`。

### 生效時機（容易誤判「改了沒反應」）

| 檔案 | 生效方式 |
|---|---|
| 全域 / 向上找到的 `AGENTS.md` | **熱更新**，下次送出前自動套用，不需重啟 |
| 探索後才載入的巢狀 `AGENTS.md` | **需開新 session** |
| `opencode.jsonc` 的 plugin / TUI 設定 | **需完全重啟** opencode |

## 注意事項

- `.venv` 是各 skill 在本機的 python 虛擬環境，**永不**提交（已被各 skill 的 `.gitignore`
  與上面的 Copy-Item 排除遮蔽）。
- 若新增了 repo 沒有的 skill，記得同步更新 `README.md` 目錄表與 `SKILLS.md` 對應章節。
- push 用 HTTPS（`origin` remote 為 https URL）。認證優先走 **`gh auth setup-git`**；
  純 git 環境則用 Git Credential Manager（`credential.helper=manager`）。
- **同步是雙向的覆寫作業**：方向一會蓋掉本機未提交的修改。若本機有想保留的改動，
  先做方向二，或先手動 diff 確認。

## 踩過的坑

| 坑 | 症狀 | 解法 |
|---|---|---|
| 文件寫死某台機器的絕對路徑 | 在別的機器上照抄，`Copy-Item` 找不到來源或寫到錯誤位置 | 路徑一律用 `Join-Path $env:USERPROFILE` 於執行時推導 |
| 以為 skills 在 `<PROJECT_ROOT_A>\.opencode\skills\` | 該磁碟機不存在，指令整個跳過 | canonical 是 `~/.config/opencode/skills/`，先確認再動作 |
| 本機**完全沒有 git** | `git : 無法辨識 'git'` | 裝 MinGit 可攜版（見 0.2），設 `$env:PATH` 後再用 |
| `gh auth setup-git` 報找不到 git | gh 需要 `git` 在 PATH 才能寫入 helper 設定 | 先把 MinGit 的 `cmd` 加進 `$env:PATH`，再跑 `gh auth setup-git` |
| GCM `--device` 沒印出 code | 非互換式環境下 stdout 沒內容，程序整個掛住 | 改用 `gh auth login --web`（code 印在 stderr 且自動複製到剪貼簿） |
| `git push` 輸出到 stderr 被判成失敗 | PowerShell 把 git 的進度訊息當成 ErrorRecord，看起來像 `Exited with code 1` | 看 `git ls-remote origin main` 與本機 `rev-parse HEAD` 是否一致；成功時 push 本身 exit code 為 0 |
| `git add -A` 把別人的變更一起推上去 | 工作區有使用者先前的修改／刪除，被混進本次 commit | 先 `git status` + `git diff` 逐項確認歸屬，分批 stage |
| 巢狀 clone 被當成一般檔案提交 | `git add -A` 把整個上游 repo 塞進本機 repo | 把巢狀 clone 目錄加進 `.gitignore` |
| remote 指向不存在的 repo | `remote: Repository not found.` | 先用 GitHub API 確認 repo 存在：`gh api repos/<owner>/<repo>`；不存在就改用可用的那個 remote |
| `git push` 被拒（non-fast-forward） | 遠端有本機沒有的 commit | 先 `git fetch` + `git pull --rebase`，解衝突後再推 |
| 多個工作階段同時改同一 skill | rebase 後檔案殘留 conflict marker 並被 commit 進去 | push 前先 fetch；rebase 後必跑 build／語法檢查，並搜 `<<<<<<<` |
| 用 PowerShell 改寫含繁中的 skill | 中文毀損，或開頭多一個 BOM 導致 frontmatter 失效 | 用編輯工具或 Node `fs.writeFileSync(p, s, 'utf8')` |
| 整併 skill 後 README 索引沒重產 | README 連結指向已刪除的目錄、新目錄沒列、`SKILLS.md` 章節編號跳號 | 跑 `python3 scripts/gen_index.py`；`--check` 通過才提交 |
| 下載時把 comsol / hcl 一起裝進本機 | 內部版不需要這兩類，卻佔了 `skills/` 目錄 | 下載迴圈加 `-notlike "comsol*"` / `-notlike "hcl-*"` |
| 在 `opencode.jsonc` 寫 `instructions` 期待生效 | 完全沒作用 | V2 接受該欄位但不載入，指令一律用 `AGENTS.md` |
| 部署 `AGENTS.md` 到公開 repo 帶出內部資訊 | 代理 IP、員工代號跟著外流 | 通用規範與機器專屬資訊分檔存放，後者留本機 |
| 改了巢狀 `AGENTS.md` 沒反應 | 巢狀檔不熱更新 | 開新 session；只有全域與向上找到的檔案會熱更新 |
| `git rebase --continue` 在 Windows 失敗 | git 透過 `sh` 呼叫編輯器，反斜線路徑被吃掉 | `-c core.editor="C:/path/noop.cmd"` 用正斜線 |

## 官方參考

- [yd7148/OpenCode_skill](https://github.com/yd7148/OpenCode_skill)

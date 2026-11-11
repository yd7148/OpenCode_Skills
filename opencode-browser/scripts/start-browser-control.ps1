<#
.SYNOPSIS
    以既有的 Chrome profile 啟動瀏覽器並載入 OpenCode Browser 擴充功能（BROWSER CONTROL）。

.DESCRIPTION
    Chrome 137+ 已移除 --load-extension，只能透過 CDP 的 Extensions.loadUnpacked
    載入未封裝擴充功能，因此需要 Chrome 帶著 --remote-debugging-port 啟動。

    本腳本：
      1. 執行期解析 Chrome 執行檔、profile 目錄、cache 目錄（不寫死任何機器路徑）
      2. 若該 profile 已被 Chrome 使用，先關閉既有實例（profile 只能被一個實例鎖定）
      3. 帶 --remote-debugging-port 啟動 Chrome
      4. 呼叫 load-extension.mjs 載入擴充功能
      5. 驗證 broker <-> 擴充功能連線

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File start-browser-control.ps1
    powershell -ExecutionPolicy Bypass -File start-browser-control.ps1 -Port 9333
#>

param(
    [int]$Port = 9222,
    [switch]$SkipClose,
    [switch]$NoVerify
)

$ErrorActionPreference = 'Stop'

function Resolve-ChromeExe {
    # 1) 正在執行的 chrome.exe（可攜版 Chrome 只能這樣取得）
    $running = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath } | Select-Object -First 1
    if ($running) { return $running.ExecutablePath }

    # 2) PATH
    $cmd = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # 3) 登錄機碼 App Paths
    $appPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe'
    )
    foreach ($key in $appPaths) {
        if (Test-Path $key) {
            $value = (Get-ItemProperty $key -ErrorAction SilentlyContinue).'(default)'
            if ($value -and (Test-Path $value)) { return $value }
        }
    }

    # 4) 標準安裝位置
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
        (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    return $null
}

function Get-ChromeProfileInfo {
    # 從執行中的 chrome.exe 命令列取得 --user-data-dir / --disk-cache-dir
    $info = @{ UserDataDir = $null; DiskCacheDir = $null }
    $proc = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match '--user-data-dir' } | Select-Object -First 1
    if ($proc -and $proc.CommandLine) {
        if ($proc.CommandLine -match '--user-data-dir="?([^"\s]+)"?') { $info.UserDataDir = $Matches[1] }
        if ($proc.CommandLine -match '--disk-cache-dir="?([^"\s]+)"?') { $info.DiskCacheDir = $Matches[1] }
    }
    if (-not $info.UserDataDir) {
        $info.UserDataDir = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data'
    }
    return $info
}

$chrome = Resolve-ChromeExe
if (-not $chrome) {
    Write-Error "找不到 Chrome 執行檔。請安裝 Chrome 或用 -SkipClose 搭配手動啟動。"
    exit 1
}

$profileInfo = Get-ChromeProfileInfo
$userDataDir = $profileInfo.UserDataDir
$diskCacheDir = $profileInfo.DiskCacheDir

$extensionDir = Join-Path $env:USERPROFILE '.opencode-browser\extension'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$loader = Join-Path $scriptDir 'load-extension.mjs'

Write-Host "[opencode-browser] Chrome   : $chrome"
Write-Host "[opencode-browser] profile : $userDataDir"
if ($diskCacheDir) { Write-Host "[opencode-browser] cache   : $diskCacheDir" }
Write-Host "[opencode-browser] port    : $Port"

# 同一個 profile 不能被兩個 Chrome 實例同時使用，先關掉既有實例
$using = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$userDataDir*" }
if ($using) {
    if ($SkipClose) {
        Write-Warning "已有 Chrome 實例使用此 profile，且旗標不會套用到既有實例。請先手動關閉 Chrome 再執行。"
    } else {
        Write-Host "[opencode-browser] 關閉既有 Chrome 實例（profile 鎖定）..."
        $using | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
    }
}

$arguments = @(
    "--user-data-dir=$userDataDir",
    "--remote-debugging-port=$Port",
    '--no-first-run',
    '--no-default-browser-check'
)
if ($diskCacheDir) { $arguments += "--disk-cache-dir=$diskCacheDir" }

Start-Process -FilePath $chrome -ArgumentList $arguments | Out-Null
Write-Host "[opencode-browser] Chrome 已啟動，等待 CDP 就緒..."

$node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = 'node' }

& $node $loader $Port $extensionDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "擴充功能載入失敗。"
    exit 1
}

if (-not $NoVerify) {
    Write-Host "[opencode-browser] 驗證 broker 連線..."
    & npx.cmd '@different-ai/opencode-browser@latest' status
}

Write-Host "[opencode-browser] 完成。CDP 端點：http://127.0.0.1:$Port"

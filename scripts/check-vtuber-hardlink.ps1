<#
.SYNOPSIS
    檢查（並可修復） VTUBER_SETUP.md 的 hardlink 是否完好。

.DESCRIPTION
    Vtuber 目錄下的 VTUBER_SETUP.md 是指向 skill 收藏庫內母檔的 NTFS hardlink，
    兩者共用同一份實體檔，所以不存在「同步」問題。

    母檔（-Repo）預設為本腳本所在 skill 根目錄下的 VTUBER_SETUP.md，
    隨腳本位置自動解析，不寫死磁碟機。
    連結（-Link）在各機器上位置不同，必須由使用者指定。

    但 git 的 checkout / restore / 切分支會用 unlink+create 取代檔案，
    從而**切斷連結**（內容仍正確，只是不再連動）。
    本腳本可偵測這個狀態並用 -Fix 重建。

.PARAMETER Fix
    偵測到連結斷裂時自動以 repo 版本重建 hardlink。

.PARAMETER Repo
    repo 內的母檔路徑（唯一真實來源）。預設為本腳本 ../VTUBER_SETUP.md。

.PARAMETER Link
    Vtuber 目錄下的捷徑路徑。各機器位置不同，必須明確指定。

.EXAMPLE
    .\check-vtuber-hardlink.ps1 -Link 'D:\2026-08-Vtuber\VTUBER_SETUP.md'
    僅檢查，連結斷裂時以 exit code 1 回報。

.EXAMPLE
    .\check-vtuber-hardlink.ps1 -Link 'D:\2026-08-Vtuber\VTUBER_SETUP.md' -Fix
    檢查並自動重建連結。
#>
[CmdletBinding()]
param(
    [switch]$Fix,
    # 母檔預設由腳本位置推導（skill 根目錄下的 VTUBER_SETUP.md）
    [string]$Repo = (Join-Path (Split-Path -Parent $PSScriptRoot) 'VTUBER_SETUP.md'),
    # 連結位置各機器不同，不設預設
    [string]$Link
)

$ErrorActionPreference = 'Stop'

if (-not $Link) {
    throw "請用 -Link 指定 Vtuber 目錄下的 VTUBER_SETUP.md（各機器位置不同，沒有合理預設值）。範例：-Link 'D:\2026-08-Vtuber\VTUBER_SETUP.md'"
}

function Get-NormalizedLinkSet {
    <# 取得指向同一實體檔的所有路徑（正規化成 \磁碟\相對路徑） #>
    param([string]$Path)
    $raw = & fsutil hardlink list $Path 2>&1
    if ($LASTEXITCODE -ne 0) { return @() }
    $set = @{}
    foreach ($line in $raw) {
        $t = ([string]$line).Trim()
        if ($t) { $set[$t.ToLowerInvariant()] = $true }
    }
    return $set
}

function Get-Norm {
    <# 內容正規化後的雜湊（忽略 CRLF/LF 差異與檔尾換行） #>
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    $text = $text -replace "`r`n", "`n"
    $text = $text.TrimEnd("`n")
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $h = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($text))
        return ([System.BitConverter]::ToString($h) -replace '-', '')
    }
    finally { $sha.Dispose() }
}

Write-Host '=== VTUBER_SETUP.md hardlink 檢查 ===' -ForegroundColor Cyan
Write-Host "  repo : $Repo"
Write-Host "  link : $Link"
Write-Host ''

# ---- 前置檢查 ----
if (-not (Test-Path -LiteralPath $Repo)) {
    Write-Host "[FAIL] repo 母檔不存在: $Repo" -ForegroundColor Red
    exit 2
}
$repoItem = Get-Item -LiteralPath $Repo

# ---- 判斷連結是否完好 ----
$linkExists = Test-Path -LiteralPath $Link
$broken = $true
$linkStatus = ''

if (-not $linkExists) {
    $linkStatus = '捷徑檔不存在'
}
else {
    $set = Get-NormalizedLinkSet -Path $Repo
    $linkFull = (Get-Item -LiteralPath $Link).FullName
    # 去掉磁碟前綴 "D:"，剩下的開頭就已經是 "\"，不要再 prepend
    $key = $linkFull.Substring(2).ToLowerInvariant()
    if ($set.ContainsKey($key)) {
        $broken = $false
        $linkStatus = '連結完好'
    }
    else {
        $linkStatus = '連結已斷（檔案各自獨立）'
    }
}

# ---- 內容一致性（無論連結是否斷裂都要看） ----
$contentSame = $false
if ($linkExists) {
    $contentSame = (Get-Norm -Path $Repo) -eq (Get-Norm -Path $Link)
}

Write-Host '--- 狀態 ---'
Write-Host ("  連結 : {0}" -f $linkStatus)
Write-Host ("  內容 : {0}" -f $(if ($linkExists) { if ($contentSame) { '一致' } else { '不一致 (repo 為準)' } } else { '無法比對' }))
Write-Host ''

# ---- 需要動作嗎 ----
$needFix = $broken -or (-not $contentSame)

if ($needFix -and -not $Fix) {
    Write-Host '[WARN] 需要重建連結。執行 -Fix 自動修復：' -ForegroundColor Yellow
    Write-Host '  .\check-vtuber-hardlink.ps1 -Fix'
    Write-Host ''
    exit 1
}

if (-not $needFix) {
    Write-Host '[OK] hardlink 完好且內容一致，無需動作。' -ForegroundColor Green
    exit 0
}

# ---- 修復 ----
Write-Host '--- 修復中 ---' -ForegroundColor Cyan

# 以 repo 母檔為唯一真實來源，覆寫捷徑路徑
if ($linkExists) {
    Copy-Item -LiteralPath $Repo -Destination $Link -Force
    Write-Host "  已以 repo 版本覆寫 $Link"
}
else {
    Copy-Item -LiteralPath $Repo -Destination $Link -Force
    Write-Host "  已建立 $Link"
}

# 必須先刪除既有檔案才能建 hardlink
Remove-Item -LiteralPath $Link -Force
New-Item -ItemType HardLink -Path $Link -Target $Repo | Out-Null
Write-Host "  已建立 hardlink -> $Repo"

# ---- 修復後驗證 ----
Write-Host ''
Write-Host '--- 修復後驗證 ---'
$set = Get-NormalizedLinkSet -Path $Repo
Write-Host '  fsutil hardlink list:'
foreach ($k in $set.Keys) { Write-Host "    $k" }

$verified = $false
if ($set.Count -ge 2) {
    $a = (Get-Norm -Path $Repo)
    $b = (Get-Norm -Path $Link)
    $verified = ($a -eq $b)
}

if ($verified) {
    Write-Host ''
    Write-Host '[OK] 連結已重建且內容一致。' -ForegroundColor Green
    exit 0
}
else {
    Write-Host ''
    Write-Host '[FAIL] 驗證未通過，請手動檢查。' -ForegroundColor Red
    exit 1
}
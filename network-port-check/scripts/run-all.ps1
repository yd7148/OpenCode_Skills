<#
.SYNOPSIS
    一鍵執行全部網路連線檢查，並輸出 Markdown 報告。

.DESCRIPTION
    依序執行 ports / services / websites / tls / bandwidth 五項檢查，
    將主控台輸出同時寫入 Markdown 報告檔。

.PARAMETER OutFile
    報告輸出路徑，預設為 <專案根>\network-check-report_<yyyyMMdd-HHmmss>.md

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File run-all.ps1
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File run-all.ps1 -OutFile D:\report.md -SkipBandwidth
#>
[CmdletBinding()]
param(
    [string]$OutFile = '',
    [switch]$SkipBandwidth,
    [switch]$SkipUpload
)

$ErrorActionPreference = 'Continue'

# --- UTF-8 stdout bootstrap -------------------------------------------------
# PowerShell 5.1 有兩個獨立的編碼點，繁體中文要正確必須兩個都處理：
#   1. [Console]::OutputEncoding — 讀取「子行程 stdout」時的解碼依據
#      （父腳本用 & powershell ... 擷取子行程輸出時靠它）
#   2. [Console]::SetOut(...)  — 本腳本自己寫出 stdout 的編碼
# 只設其中一個都不完整；只設 [Console]::OutputEncoding 亦無效（redirect 時）。
if ($PSVersionTable.PSVersion.Major -lt 6) {
    $Utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [Console]::OutputEncoding = $Utf8NoBom
    $Utf8Out = New-Object System.IO.StreamWriter([Console]::OpenStandardOutput(), $Utf8NoBom)
    $Utf8Out.AutoFlush = $true
    [Console]::SetOut($Utf8Out)
    $OutputEncoding = $Utf8NoBom
}
# ---------------------------------------------------------------------------


$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutFile) {
    $OutFile = Join-Path $env:USERPROFILE ("network-check-report_{0}.md" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
}

$net = $null
try {
    $ip  = Get-NetIPAddress -AddressFamily IPv4 |
           Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notlike '169.254.*' } |
           Select-Object -First 1
    $gw  = Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1
    $dns = (Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses } |
            Select-Object -First 1 -ExpandProperty ServerAddresses) -join ', '
    $net = [pscustomobject]@{ IP = $ip.IPAddress; GW = $gw.NextHop; DNS = $dns }
} catch { }

$sb = New-Object System.Text.StringBuilder
function Append-Section {
    param([string]$Title, [string]$Content)
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("## $Title")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine($Content.TrimEnd())
    [void]$sb.AppendLine('```')
}

$stages = @(
    @{ Title = '對外 Port 連通性矩陣';       Script = 'test-ports.ps1';     Args = @() },
    @{ Title = '遠端服務（RDP / SSH / 通道）'; Script = 'test-services.ps1'; Args = @() },
    @{ Title = '網站可達性';                Script = 'test-websites.ps1';  Args = @() },
    @{ Title = 'TLS 憑證 / MITM 檢查';     Script = 'test-tls.ps1';       Args = @() }
)
if (-not $SkipBandwidth) {
    $stages += @{ Title = '頻寬 / 延遲 / 路由'; Script = 'test-bandwidth.ps1'; Args = $(if ($SkipUpload) { @('-SkipUpload') } else { @() }) }
}

Write-Output "=== 網路連線檢查 ==="
Write-Output "開始時間：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Output ""

function Invoke-Stage {
    <#
      以「位元組層級」轉向執行子腳本，再用 UTF-8 讀回。
      不要用 & powershell ... | Out-String 擷取：PowerShell 5.1 對原生程式
      stdout 的解碼在 redirect 情境下並不可靠，會把子腳本的繁中輸出轉成亂碼。
      Start-Process -RedirectStandardOutput 是在 OS 層把原始位元組寫進檔案，
      再由我們明確指定 UTF-8 解碼，才保證正確。
    #>
    param([string]$ScriptPath, [string[]]$Arguments = @())

    $stdout = [IO.Path]::GetTempFileName()
    $stderr = [IO.Path]::GetTempFileName()
    try {
        $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$ScriptPath`"")
        foreach ($a in $Arguments) { $argList += $a }
        Start-Process -FilePath 'powershell' -ArgumentList $argList -NoNewWindow -Wait `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null

        $text = [IO.File]::ReadAllText($stdout, [Text.Encoding]::UTF8)
        $err  = [IO.File]::ReadAllText($stderr, [Text.Encoding]::UTF8)
        if ($err.Trim()) { $text += "`n[stderr]`n$err" }
        return $text
    } finally {
        Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue
    }
}

foreach ($s in $stages) {
    $path = Join-Path $ScriptDir $s.Script
    if (-not (Test-Path $path)) { Write-Warning "找不到腳本：$path"; continue }

    Write-Output ">>> 執行 $($s.Script) ..."
    $out = Invoke-Stage -ScriptPath $path -Arguments $s.Args
    Write-Output $out
    Append-Section -Title $s.Title -Content $out
}

# --- 產生 Markdown 報告 ---
$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine('# 對外網路連線檢查報告')
[void]$md.AppendLine('')
[void]$md.AppendLine("產生時間：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  ")
[void]$md.AppendLine("產生工具：network-port-check skill（opencode agent）")
if ($net) {
    [void]$md.AppendLine('')
    [void]$md.AppendLine('| 項目 | 值 |')
    [void]$md.AppendLine('|------|-----|')
    [void]$md.AppendLine("| 本機 IP | ``$($net.IP)`` |")
    [void]$md.AppendLine("| 預設閘道 | ``$($net.GW)`` |")
    [void]$md.AppendLine("| DNS | ``$($net.DNS)`` |")
}
[void]$md.AppendLine($sb.ToString())
[void]$md.AppendLine('')
[void]$md.AppendLine('---')
[void]$md.AppendLine('')
[void]$md.AppendLine('> 本報告由 `test-ports` / `test-services` / `test-websites` / `test-tls` / `test-bandwidth` 原始輸出組成。')
[void]$md.AppendLine('> 判讀方式請見 skill 的 `reference/interpretation.md`。')

$utf8Bom = New-Object System.Text.UTF8Encoding $true
[IO.File]::WriteAllText($OutFile, $md.ToString(), $utf8Bom)

Write-Output ''
Write-Output "=== 完成 ==="
Write-Output "報告已存：$OutFile"
Write-Output "完成時間：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

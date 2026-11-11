<#
.SYNOPSIS
    對外 Port 連通性矩陣（完全並行）。

.DESCRIPTION
    一次開啟所有 TcpClient，再用 WaitHandle 批次等待，避免 Test-NetConnection
    逐一等待造成的超時。分批 (chunk) 處理以相容 .NET WaitHandle 句柄上限。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File test-ports.ps1
#>
[CmdletBinding()]
param(
    [string[]]$Ports = @('21','22','25','53','80','110','123','143','389','443','445','587','636',
                         '993','995','1433','1521','3306','3389','5432','5900','5985','6379',
                         '8080','8443','8888','27017'),
    [int]$TimeoutMs = 5000,
    [string[]]$ExtraHosts = @()
)

# `powershell -File x.ps1 -ExtraHosts "a,b"` 會把整串當成單一元素，故自行再切一次
if ($ExtraHosts) { $ExtraHosts = @(($ExtraHosts -join ',') -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }

$ErrorActionPreference = 'SilentlyContinue'

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


# 取得本機 IPv4 與 gateway，自動加入測試目標
function Get-NetContext {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notlike '169.254.*' } |
          Select-Object -First 1
    $gw = Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1
    [pscustomobject]@{ IP = $ip.IPAddress; Gateway = $gw.NextHop }
}

$net = Get-NetContext

$targets = @(
    @{ Name = '8.8.8.8 (Google DNS)';          Host = '8.8.8.8' }
    @{ Name = '1.1.1.1 (Cloudflare)';         Host = '1.1.1.1' }
    @{ Name = '8.9.9.9 (Quad9)';              Host = '8.9.9.9' }
    @{ Name = 'github.com';                   Host = 'github.com' }
    @{ Name = 'www.microsoft.com';            Host = 'www.microsoft.com' }
    @{ Name = 'tw.yahoo.com';                 Host = 'tw.yahoo.com' }
    @{ Name = "gw $($net.Gateway) (LAN)";     Host = $net.Gateway }
)
foreach ($h in $ExtraHosts) { $targets += @{ Name = $h; Host = $h } }

Write-Output "本機 IP : $($net.IP)"
Write-Output "Gateway : $($net.Gateway)"
Write-Output "目標數  : $($targets.Count)   Port 數: $($Ports.Count)   Timeout: ${TimeoutMs}ms`n"

# --- 建立所有連線 ---
$pending = New-Object System.Collections.ArrayList
foreach ($t in $targets) {
    foreach ($p in $Ports) {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.BeginConnect($t.Host, [int]$p, $null, $null) | Out-Null
        [void]$pending.Add([pscustomobject]@{
            Target = $t.Name; Host = $t.Host; Port = $p
            Client = $c; Wait = $c.Client.AsyncWaitHandle
        })
    }
}

# --- 分批等待（每批 60 個，避開 WaitHandle 句柄數上限）---
$ChunkSize = 60
for ($i = 0; $i -lt $pending.Count; $i += $ChunkSize) {
    $end = [Math]::Min($i + $ChunkSize, $pending.Count)
    $slice = @($pending[$i..($end - 1)])
    try { [System.Threading.WaitHandle]::WaitAll([System.Threading.WaitHandle[]]$slice.Wait, $TimeoutMs) | Out-Null }
    catch { $slice | ForEach-Object { try { $_.Wait.WaitOne($TimeoutMs) | Out-Null } catch {} } }
}

# --- 收集結果 ---
$results = foreach ($i in $pending) {
    $open = $i.Client.Connected
    $i.Client.Close()
    [pscustomobject]@{ Target = $i.Target; Port = $i.Port; Open = $open }
}

# --- 輸出矩陣 ---
$hdr = ($Ports | ForEach-Object { '{0,-6}' -f $_ }) -join ''
Write-Output ('=== OUTBOUND PORT MATRIX  (OK = 可連線, X = 被封鎖/拒絕/逾時) ===')
Write-Output ''
Write-Output ('{0,-30} {1}' -f 'TARGET', $hdr)
foreach ($t in $targets) {
    $line = '{0,-30} ' -f $t.Name
    foreach ($p in $Ports) {
        $row = $results | Where-Object { $_.Target -eq $t.Name -and $_.Port -eq $p }
        $line += if ($row.Open) { '{0,-6}' -f 'OK' } else { '{0,-6}' -f 'X' }
    }
    Write-Output $line
}

$okPorts   = $Ports | Where-Object { $p = $_; $results | Where-Object { $_.Port -eq $p -and $_.Open } }
$badPorts  = $Ports | Where-Object { $p = $_; -not ($results | Where-Object { $_.Port -eq $p -and $_.Open }) }

Write-Output ''
Write-Output '=== 可連線的 Port ==='
if ($okPorts) { $okPorts -join '  ' } else { '(無)' }

Write-Output ''
Write-Output '=== 被封鎖的 Port ==='
if ($badPorts) { $badPorts -join '  ' } else { '(無)' }

Write-Output ''
Write-Output '=== 結論 ==='
$okCount = @($okPorts).Count
if ($okCount -le 3 -and $badPorts -match '^(22|3389|5900)$') {
    Write-Output "典型白名單 ACL 防火牆：只放行 $($okPorts -join ',')，遠端管理協定（SSH/RDP/VNC）全數封鎖。"
    Write-Output '替代方案需走 HTTPS 443（Tailscale / ZeroTier / ngrok / AWS SSM / Google IAP）。'
} else {
    Write-Output "開放 Port 數：$okCount / $($Ports.Count)"
}

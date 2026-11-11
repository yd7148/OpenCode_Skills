<#
.SYNOPSIS
    頻寬（上/下載）、延遲（ping / TCP handshake）與路由路徑測試。

.DESCRIPTION
    全部使用 curl.exe 量測，並以 %{time_namelookup} / %{time_connect} /
    %{time_appconnect} / %{time_starttransfer} 分解各階段耗時。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File test-bandwidth.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipUpload,
    [int]$DownloadBytes = 50000000
)

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


$curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
if (-not $curl) { $curl = "$env:SystemRoot\System32\curl.exe" }
if (-not (Test-Path $curl)) { Write-Error '找不到 curl.exe，無法測量頻寬。'; exit 1 }

function Measure-Curl {
    param([string]$Url, [switch]$Upload, [string]$TempFile, [int]$MaxTime = 60)
    # 索引：0 code 1 size_down 2 speed_down 3 dns 4 conn 5 tls 6 ttfb 7 total 8 size_up 9 speed_up
    $fmt = '%{http_code}|%{size_download}|%{speed_download}|%{time_namelookup}|%{time_connect}|%{time_appconnect}|%{time_starttransfer}|%{time_total}|%{size_upload}|%{speed_upload}'
    $args = @('-s','-o','NUL','-w',$fmt)
    if ($Upload) { $args += @('-X','POST','--data-binary',"@$TempFile",'--max-time',"$MaxTime") }
    else { $args += @('--max-time',"$MaxTime") }
    $args += $Url
    $out = & $curl @args 2>&1
    return ,(($out -join '').Split('|'))
}

# =====================================================================
Write-Output '=== 1. 下載頻寬 ==='
Write-Output ''

$dlTests = @(
    @{ n = 'Cloudflare';  u = "https://speed.cloudflare.com/__down?bytes=$DownloadBytes" }
    @{ n = 'CacheFly';    u = 'http://cachefly.cachefly.net/50mb.test' }
    @{ n = 'Hetzner (DE)';u = 'https://speed.hetzner.de/100MB.bin' }
    @{ n = 'Gcore';       u = 'https://speed.gcore.com/50mb.bin' }
)

$dlResults = @()
foreach ($t in $dlTests) {
    $p = Measure-Curl $t.u
    if ($p[0] -eq '200' -and [double]$p[2] -gt 0) {
        $mbps   = [math]::Round([double]$p[2] * 8 / 1e6, 1)
        $sizeMB = [math]::Round([double]$p[1] / 1MB, 1)
        $total  = [math]::Round([double]$p[7], 2)
        $ttfb   = [math]::Round([double]$p[6], 2)
        $dlResults += $mbps
        Write-Output ('  {0,-16} {1,6} MB / {2,6}s  =>  {3,7} Mbps   (首包 {4}s)' -f $t.n, $sizeMB, $total, $mbps, $ttfb)
    } else {
        Write-Output ('  {0,-16} FAILED (http={1})' -f $t.n, $p[0])
    }
}

# =====================================================================
if (-not $SkipUpload) {
    Write-Output ''
    Write-Output '=== 2. 上傳頻寬 ==='
    Write-Output ''

    $tmp = Join-Path $env:TEMP ("oc-up-{0}.bin" -f (Get-Random))
    New-Item -ItemType Directory -Force -Path (Split-Path $tmp) | Out-Null
    try {
        $buf = New-Object byte[] (20MB)
        (New-Object Random 42).NextBytes($buf)
        [IO.File]::WriteAllBytes($tmp, $buf)

        $p = Measure-Curl 'https://speed.cloudflare.com/__up' -Upload -TempFile $tmp -MaxTime 60
        if ($p[0] -eq '200' -and [double]$p[9] -gt 0) {
            Write-Output ('  上傳 {0} MB / {1}s  =>  {2} Mbps' -f [math]::Round([double]$p[8]/1MB,1), [math]::Round([double]$p[7],2), [math]::Round([double]$p[9]*8/1e6,1))
        } else {
            Write-Output ('  上傳測試 FAILED (http={0} speed_up={1})' -f $p[0], $p[9])
        }
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

# =====================================================================
Write-Output ''
Write-Output '=== 3. 延遲（TCP handshake，curl %{time_connect}）==='
Write-Output ''

foreach ($h in @('1.1.1.1', '8.8.8.8', 'www.google.com', 'github.com', 'www.microsoft.com', 'tw.yahoo.com')) {
    $o = & $curl -s -o NUL -w '%{time_connect}' --max-time 10 "https://$h/" 2>&1
    $ms = [math]::Round([double]($o -join '') * 1000, 1)
    Write-Output ('  {0,-22} {1,8} ms' -f $h, $ms)
}

Write-Output ''
Write-Output '  ICMP ping：'
foreach ($h in @('1.1.1.1', '8.8.8.8', 'www.google.com')) {
    $p = Test-Connection -ComputerName $h -Count 3 -ErrorAction SilentlyContinue
    if ($p) {
        $avg = [math]::Round((($p | Measure-Object -Property ResponseTime -Average).Average), 1)
        Write-Output ('    {0,-22} avg RTT = {1} ms' -f $h, $avg)
    } else {
        Write-Output ('    {0,-22} ICMP 不回應（常見的 ICMP 過濾，非連線問題）' -f $h)
    }
}

# =====================================================================
Write-Output ''
Write-Output '=== 4. 路由路徑（tracert）==='
Write-Output ''
$target = '1.1.1.1'
Write-Output "  目標：$target"
try {
    $t = tracert -d -h 12 -w 800 $target
    foreach ($line in ($t | Select-Object -Skip 1)) { if ($line.Trim()) { Write-Output ("    {0}" -f $line.Trim()) } }
} catch { Write-Output '  tracert 執行失敗' }

# =====================================================================
Write-Output ''
Write-Output '=== 5. 頻寬結論 ==='
Write-Output ''
if ($dlResults) {
    $best = ($dlResults | Measure-Object -Maximum).Maximum
    $avg  = [math]::Round((($dlResults | Measure-Object -Average).Average), 1)
    Write-Output ("  下載峰值 {0} Mbps，平均 {1} Mbps" -f $best, $avg)
    if ($best -ge 300)      { Write-Output '  => 商業光纖水準，頻寬不是瓶頸。' }
    elseif ($best -ge 100)  { Write-Output '  => 一般寬頻水準。' }
    else                    { Write-Output '  => 頻寬偏低，大檔下載會明顯偏慢。' }
} else {
    Write-Output '  所有測速主機皆無回應（部分主機會封鎖來自特定地區的連線），無法測量下載頻寬。'
    Write-Output '  建議改用 speedtest.net 或向網路管理員確認實際速率。'
}

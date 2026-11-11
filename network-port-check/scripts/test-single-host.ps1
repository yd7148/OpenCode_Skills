<#
.SYNOPSIS
    單一網站／雲端服務連不上時的歸因診斷。

.DESCRIPTION
    處理「整體網路正常，但只有某一個網站連不上」的情況。
    依序執行五層流程，用分組對照 + GeoIP/ASN 判定責任歸屬：

      1. 症狀層   DNS / ICMP / TCP 80 / TCP 443
      2. 對照層   同組織其他站台（決定責任歸屬的關鍵）
      3. GeoIP    解析到的 IP 屬於哪個國家／ASN
      4. 排除層   本機防火牆 / Proxy / DNS 污染
      5. 結論     自動輸出責任歸屬與行動建議

    完整判讀說明見 reference/single-host-triage.md

.PARAMETER Target
    目標主機名稱，例如 pan.quark.cn

.PARAMETER Control
    對照組主機（逗號分隔）。應為「同一組織」的其他站台，
    例如 www.quark.cn,www.aliyun.com

.PARAMETER Url
    完整 URL，用於 HTTP 實測（可省略）

.PARAMETER TimeoutMs
    TCP 連線逾時（毫秒），預設 6000

.EXAMPLE
    # 基本用法
    .\test-single-host.ps1 -Target pan.quark.cn -Control www.quark.cn,www.aliyun.com

    # 帶 HTTP 實測
    .\test-single-host.ps1 -Target pan.quark.cn -Control www.quark.cn `
        -Url "https://pan.quark.cn/s/xxxxx"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Control = '',
    [string]$Url = '',
    [int]$TimeoutMs = 6000
)

$ErrorActionPreference = 'SilentlyContinue'

# --- UTF-8 stdout bootstrap -------------------------------------------------
# PowerShell 5.1 有兩個獨立的編碼點，繁體中文要正確必須兩個都處理：
#   1. [Console]::OutputEncoding — 讀取「子行程 stdout」時的解碼依據
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

function Test-TcpPort {
    param([string]$Target, [int]$Port, [int]$Timeout = 5000)
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $r = $c.BeginConnect($Target, $Port, $null, $null)
        if ($r.AsyncWaitHandle.WaitOne($Timeout, $false)) {
            $c.EndConnect($r) | Out-Null
            return $true
        }
    } catch { }
    finally { $c.Close() }
    return $false
}

function Resolve-Ip {
    param([string]$HostName)
    $parsed = $null
    if ([Net.IPAddress]::TryParse($HostName, [ref]$parsed)) { return $HostName }
    # 注意：不可寫成 $ips[0]。PowerShell 會把單一結果 unroll 成字串，
    # $ips[0] 取到的是「第一個字元」（例如 "20.1.2.3"[0] => "2"）。
    return (Resolve-DnsName $HostName -Type A -ErrorAction SilentlyContinue |
            Where-Object IPAddress | Select-Object -First 1 -ExpandProperty IPAddress)
}

function Get-GeoIp {
    param([string]$Ip)
    try {
        $j = & curl.exe -sS -m 12 "https://ipinfo.io/$Ip/json" 2>$null | ConvertFrom-Json
        if ($j -and $j.country) { return $j }
    } catch { }
    return $null
}

# 透過 -File 傳入的逗號分隔字串會被當成單一元素，必須自行再切
$controlList = @()
if ($Control) { $controlList = $Control -split ',' | Where-Object { $_ } | ForEach-Object { $_.Trim() } }

$start = Get-Date

# =====================================================================
Write-Output '============================================================'
Write-Output "  1. 症狀層 — 目標主機 $Target"
Write-Output '============================================================'

$ip = Resolve-Ip $Target
if (-not $ip) {
    Write-Output "  DNS 解析 : 失敗"
    Write-Output "  => 網域可能不存在或已廢棄，這不是網路問題。"
    exit 1
}
Write-Output "  DNS 解析   : $ip  OK"

$icmp = Test-Connection -ComputerName $ip -Count 3 -ErrorAction SilentlyContinue
Write-Output ("  ICMP ping  : {0}" -f $(if ($icmp) { '有回應' } else { 'TIMEOUT' }))

foreach ($p in 80, 443) {
    $ok = Test-TcpPort $ip $p $TimeoutMs
    Write-Output ("  TCP {0,-6} : {1}" -f $p, $(if ($ok) { '連線成功' } else { 'TIMEOUT / 被拒' }))
}

if ($Url) {
    Write-Output '  HTTP 實測  :'
    & curl.exe -sS -m 25 -o NUL -w "      HTTP %{http_code}  time=%{time_total}s`n" $Url 2>&1 |
        ForEach-Object { Write-Output "      $_" }
}

# =====================================================================
Write-Output ''
Write-Output '============================================================'
Write-Output '  2. 對照層 — 同組織其他站台（責任歸屬的關鍵證據）'
Write-Output '============================================================'

if ($controlList.Count -eq 0) {
    Write-Output '  [警告] 未提供對照組。'
    Write-Output '         沒有對照組就無法判定是「服務端問題」還是「本機／網路問題」。'
    Write-Output '         請用 -Control 重新指定同一組織的其他站台。'
} else {
    $controlPass = 0
    foreach ($h in $controlList) {
        $cip = Resolve-Ip $h
        if (-not $cip) { Write-Output ("  {0,-24} DNS FAIL" -f $h); continue }
        $ok = Test-TcpPort $cip 443 $TimeoutMs
        if ($ok) { $controlPass++ }
        Write-Output ("  {0,-24} {1,-17} 443 = {2}" -f $h, $cip, $(if ($ok) { '通' } else { '不通' }))
    }
    Write-Output ''
    $controlTotal = @($controlList).Count
    Write-Output "  對照組可通數：$controlPass / $controlTotal"
}

# =====================================================================
Write-Output ''
Write-Output '============================================================'
Write-Output '  3. GeoIP — 解析到的 IP 落在哪裡'
Write-Output '============================================================'

$ipsToCheck = @($ip)
foreach ($h in $controlList) {
    $cip = Resolve-Ip $h
    if ($cip -and ($ipsToCheck -notcontains $cip)) { $ipsToCheck += $cip }
}

foreach ($x in $ipsToCheck) {
    $g = Get-GeoIp $x
    if ($g) {
        $tag = if ($controlList.Count -gt 0 -and $x -eq $ip) { '  <- 目標' } else { '' }
        Write-Output ("  {0,-17} {1,-3}/{2,-11} {3}{4}" -f $x, $g.country, $g.region, $g.org, $tag)
    } else {
        Write-Output ("  {0,-17} GeoIP 查詢失敗（可能需要網路或 API 限流）" -f $x)
    }
}

# =====================================================================
Write-Output ''
Write-Output '============================================================'
Write-Output '  4. 排除層 — 確認不是本機因素'
Write-Output '============================================================'

$blocks = @(Get-NetFirewallRule -Direction Outbound -Enabled True -ErrorAction SilentlyContinue |
            Where-Object { $_.Action -eq 'Block' })
if ($blocks.Count -gt 0) {
    Write-Output "  [!] 發現 $($blocks.Count) 條 Outbound Block 規則："
    $blocks | Select-Object -First 5 | ForEach-Object { Write-Output "      $($_.DisplayName)" }
} else {
    Write-Output '  [OK] 無任何 Outbound Block 規則'
}
Get-NetFirewallProfile | ForEach-Object {
    Write-Output ("      Profile {0,-8} DefaultOutbound = {1}" -f $_.Name, $_.DefaultOutboundAction)
}

$ie = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
if ($ie.ProxyEnable -eq 0 -and -not $ie.ProxyServer) { Write-Output '  [OK] 未設定 Proxy' }
else { Write-Output "  [!] 存在 Proxy : $($ie.ProxyServer)" }

foreach ($resolver in @(
    "https://dns.google/resolve?name=$Target&type=A",
    "https://cloudflare-dns.com/dns-query?name=$Target&type=A")) {
    $r = & curl.exe -sS -m 12 -H 'accept: application/dns-json' $resolver 2>$null
    if ($r) {
        $j = $r | ConvertFrom-Json
        $ips = ($j.Answer | Where-Object { $_.type -eq 1 } | ForEach-Object { $_.data }) -join ','
        $who = ($resolver -split '/')[2]
        Write-Output "      DNS $who -> $ips"
    }
}

# =====================================================================
Write-Output ''
Write-Output '============================================================'
Write-Output '  5. 結論'
Write-Output '============================================================'

$targetReachable = (Test-TcpPort $ip 443 $TimeoutMs)
$allControls = $true
foreach ($h in $controlList) {
    $cip = Resolve-Ip $h
    if ($cip -and -not (Test-TcpPort $cip 443 $TimeoutMs)) { $allControls = $false }
}

if ($targetReachable) {
    Write-Output '  目標 443 可連線。若使用者仍無法操作，問題在 HTTP 層'
    Write-Output '  （需登入／反爬蟲／權限），不是網路問題。'
} elseif ($controlList.Count -gt 0 -and $allControls) {
    Write-Output '  => 對照組全通、目標不通：責任在服務端。'
    Write-Output ''
    Write-Output '     請看上方 GeoIP：若目標 IP 落在與對照組不同的國家／ASN，'
    Write-Output '     即為服務商 geo-routing 把你的流量派到不對外開放的機房。'
    Write-Output ''
    Write-Output '     建議：'
    Write-Output '       1. 向服務商客服申訴，附上對照組證據表'
    Write-Output '       2. 請對方改用其他雲端／平台'
    Write-Output '       3. 確認該服務是否需要登入 Cookie 才有完整功能'
} elseif ($controlList.Count -gt 0 -and -not $allControls) {
    Write-Output '  => 對照組也不全通：可能為本機或網路層問題，請先確認防火牆／Proxy。'
} else {
    Write-Output '  => 目標不通，但缺少對照組，無法判定責任歸屬。'
    Write-Output '     請補上 -Control 參數（同組織其他站台）後重新執行。'
}

$elapsed = (Get-Date) - $start
Write-Output ''
Write-Output ("  耗時 {0} 秒。完整判讀見 reference/single-host-triage.md" -f [math]::Round($elapsed.TotalSeconds, 1))

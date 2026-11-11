<#
.SYNOPSIS
    遠端服務（Remote Desktop / SSH / 通道工具）可用性深度測試。

.DESCRIPTION
    1. 本機 RDP Server 狀態（listener、登錄機碼、服務、防火牆規則）
    2. 對外 3389 / 22 / 5900 連線測試
    3. 走 443 的替代通道（SSH-over-443、VPN、隧道、Session Manager）

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File test-services.ps1
#>
[CmdletBinding()]
param([int]$TimeoutMs = 8000)

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
    # 已是 IP 文字就直接用，不必（也不應該）丟給 DNS 解析
    $parsed = $null
    if ([Net.IPAddress]::TryParse($HostName, [ref]$parsed)) { return $HostName }
    # 注意：不可寫成 $ips[0]。PowerShell 會把單一結果 unroll 成字串，
    # $ips[0] 取到的是「第一個字元」（例如 "20.1.2.3"[0] => "2"）。
    return (Resolve-DnsName $HostName -Type A -ErrorAction SilentlyContinue |
            Where-Object IPAddress | Select-Object -First 1 -ExpandProperty IPAddress)
}

# =====================================================================
Write-Output '=== 1. 本機 Remote Desktop 狀態 ==='
Write-Output ''

$listener = Get-NetTCPConnection -State Listen -LocalPort 3389 -ErrorAction SilentlyContinue
if ($listener) {
    Write-Output '  [監聽中] 3389 有本機 listener：'
    $listener | ForEach-Object { Write-Output ("      {0}:{1}" -f $_.LocalAddress, $_.LocalPort) }
} else {
    Write-Output '  [未監聽] 3389 沒有本機 listener'
}

$deny = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -ErrorAction SilentlyContinue).fDenyTSConnections
$denyText = switch ($deny) { 0 { '0 = 已允許' } 1 { '1 = 已停用' } default { '未設定（預設停用）' } }
Write-Output ("  fDenyTSConnections : {0}" -f $denyText)
Write-Output ("  TermService 服務   : {0}" -f (Get-Service TermService -ErrorAction SilentlyContinue).Status)

$fwRules = @(Get-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue | Where-Object Enabled -eq True)
if ($fwRules) {
    Write-Output ("  防火牆 RDP 規則     : {0} 條啟用" -f $fwRules.Count)
} else {
    Write-Output '  防火牆 RDP 規則     : 0 條啟用（遠端連入會被擋）'
}

$rdpUsable = ($listener -and $deny -eq 0 -and $fwRules.Count -gt 0)
Write-Output ''
Write-Output ("  => 本機可當 RDP 主機被連入：{0}" -f $(if ($rdpUsable) { '可以' } else { '不行（需管理員權限開啟）' }))

# =====================================================================
Write-Output ''
Write-Output '=== 2. 遠端管理協定 對外連線 ==='
Write-Output ''

$mgmt = @(
    @{ Port = 3389; Label = 'RDP (Windows 遠端桌面)'; Hosts = @('8.8.8.8','1.1.1.1','13.107.6.1') }
    @{ Port = 22;   Label = 'SSH';                     Hosts = @('github.com','ssh.github.com') }
    @{ Port = 5900; Label = 'VNC';                     Hosts = @('8.8.8.8') }
    @{ Port = 9418; Label = 'git:// protocol';         Hosts = @('github.com') }
)

foreach ($m in $mgmt) {
    foreach ($h in $m.Hosts) {
        $ip = Resolve-Ip $h
        $verdict = if (-not $ip) { 'DNS FAIL' }
                   elseif (Test-TcpPort $ip $m.Port $TimeoutMs) { 'OPEN' }
                   else { 'BLOCKED' }
        Write-Output ("  {0,-6} -> {1,-22} {2}" -f $m.Port, $h, $verdict)
    }
}

# =====================================================================
Write-Output ''
Write-Output '=== 3. 走 HTTPS 443 的替代通道（白名單環境的唯一生路）==='
Write-Output ''

$tunnels = @(
    @{ Name = 'GitHub SSH-over-443';   Host = 'ssh.github.com' }
    @{ Name = 'Tailscale DERP';        Host = 'derp.tailscale.com' }
    @{ Name = 'ZeroTier';              Host = 'my.zerotier.com' }
    @{ Name = 'Twingate';              Host = 'twingate.com' }
    @{ Name = 'ngrok';                 Host = 'ngrok.io' }
    @{ Name = 'Cloudflare Tunnel';     Host = 'trycloudflare.com' }
    @{ Name = 'AWS SSM (Session Mgr)'; Host = 'ssm.us-east-1.amazonaws.com' }
    @{ Name = 'Google Cloud IAP';      Host = 'iap.googleapis.com' }
    @{ Name = 'Microsoft Update';      Host = 'fe2cr.update.microsoft.com' }
)

$available = @()
foreach ($t in $tunnels) {
    $ip = Resolve-Ip $t.Host
    if (-not $ip) { Write-Output ("  {0,-24} 443 -> DNS FAIL" -f $t.Name); continue }
    $ok = Test-TcpPort $ip 443 $TimeoutMs
    if ($ok) { $available += $t.Name }
    Write-Output ("  {0,-24} 443 -> {1}" -f $t.Name, $(if ($ok) { 'OPEN' } else { 'BLOCKED' }))
}

Write-Output ''
if ($available.Count -gt 0) {
    Write-Output '  可用替代方案（走 443 即可繞過 22/3389 封鎖）：'
    $available | ForEach-Object { Write-Output "      - $_" }
}

# =====================================================================
Write-Output ''
Write-Output '=== 4. 結論 ==='
Write-Output ''
if (-not (Test-TcpPort (Resolve-Ip 'github.com') 22 $TimeoutMs)) {
    if (Test-TcpPort (Resolve-Ip 'ssh.github.com') 443 $TimeoutMs) {
        Write-Output '  * SSH(22) 封鎖但 ssh.github.com:443 開放，可改走 443：'
        Write-Output '      ssh -p 443 git@ssh.github.com'
        Write-Output '    git config --global url."https://ssh.github.com:443".insteadOf "git@github.com:"'
    }
}
if (-not (Test-TcpPort '8.8.8.8' 3389 $TimeoutMs)) {
    Write-Output '  * RDP(3389) 封鎖，遠端桌面請改用 443 通道工具（上表 OPEN 者）。'
    if (-not $rdpUsable) {
        Write-Output '  * 本機 RDP Server 也未啟用（listener / 登錄機碼 / 防火牆規則 三者缺一），無法被連入。'
    }
}

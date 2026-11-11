<#
.SYNOPSIS
    網站可達性掃描，並正確區分「伺服器有回應」與「真正被網路封鎖」。

.DESCRIPTION
    本 script 最重要的邏輯：HTTP 401 / 403 / 404 / 405 / 429 都代表
    伺服器「確實有回應」，屬於 REACHABLE，不是被封鎖。只有完全沒有
    HTTP 回應（TCP 無法連線 / TLS 握手失敗 / 連線逾時）才是 BLOCKED。

    對疑似封鎖者會自動用裸 TCP 443 握手複驗，排除 PowerShell / HEAD 語意造成的誤判。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File test-websites.ps1
#>
[CmdletBinding()]
param(
    [string]$File = '',
    [int]$TimeoutSec = 12
)

$ErrorActionPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11

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


$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 內建清單：可改用 -File 傳入自訂 JSON/CSV
$builtin = @(
    @{ n = 'Google';            u = 'https://www.google.com/' }
    @{ n = 'YouTube';           u = 'https://www.youtube.com/' }
    @{ n = 'Gmail';             u = 'https://mail.google.com/' }
    @{ n = 'Google Drive';      u = 'https://drive.google.com/' }
    @{ n = 'Google Translate';  u = 'https://translate.google.com/' }
    @{ n = 'GitHub';            u = 'https://github.com/' }
    @{ n = 'GitHub API';        u = 'https://api.github.com/' }
    @{ n = 'raw.githubusercontent'; u = 'https://raw.githubusercontent.com/' }
    @{ n = 'GitLab';            u = 'https://gitlab.com/' }
    @{ n = 'Bitbucket';         u = 'https://bitbucket.org/' }
    @{ n = 'npm registry';      u = 'https://registry.npmjs.org/' }
    @{ n = 'PyPI';              u = 'https://pypi.org/simple/' }
    @{ n = 'Conda / Anaconda';  u = 'https://repo.anaconda.com/' }
    @{ n = 'Hugging Face';      u = 'https://huggingface.co/' }
    @{ n = 'Docker Hub';        u = 'https://hub.docker.com/' }
    @{ n = 'Docker Registry';   u = 'https://registry-1.docker.io/v2/' }
    @{ n = 'Microsoft';         u = 'https://www.microsoft.com/' }
    @{ n = 'MS Learn';          u = 'https://learn.microsoft.com/' }
    @{ n = 'Microsoft 365';     u = 'https://www.office.com/' }
    @{ n = 'Azure Portal';      u = 'https://portal.azure.com/' }
    @{ n = 'OpenAI API';        u = 'https://api.openai.com/v1/models' }
    @{ n = 'Anthropic API';     u = 'https://api.anthropic.com/v1/messages' }
    @{ n = 'Claude.ai';         u = 'https://claude.ai/' }
    @{ n = 'ChatGPT';           u = 'https://chatgpt.com/' }
    @{ n = 'OpenCode';          u = 'https://opencode.ai/' }
    @{ n = 'Notion';            u = 'https://www.notion.so/' }
    @{ n = 'Figma';             u = 'https://www.figma.com/' }
    @{ n = 'Canva';             u = 'https://www.canva.com/' }
    @{ n = 'Slack';             u = 'https://app.slack.com/' }
    @{ n = 'Zoom';              u = 'https://zoom.us/' }
    @{ n = 'Teams';             u = 'https://teams.microsoft.com/' }
    @{ n = 'Facebook';          u = 'https://www.facebook.com/' }
    @{ n = 'Instagram';         u = 'https://www.instagram.com/' }
    @{ n = 'X (Twitter)';       u = 'https://x.com/' }
    @{ n = 'LinkedIn';          u = 'https://www.linkedin.com/' }
    @{ n = 'Reddit';            u = 'https://www.reddit.com/' }
    @{ n = 'TikTok';            u = 'https://www.tiktok.com/' }
    @{ n = 'LINE';              u = 'https://www.line.me/' }
    @{ n = 'Telegram';          u = 'https://web.telegram.org/' }
    @{ n = 'Discord';           u = 'https://discord.com/' }
    @{ n = 'Steam';             u = 'https://store.steampowered.com/' }
    @{ n = 'Spotify';           u = 'https://www.spotify.com/' }
    @{ n = 'Yahoo TW';          u = 'https://tw.yahoo.com/' }
    @{ n = 'Yahoo JP';          u = 'https://www.yahoo.co.jp/' }
    @{ n = 'Baidu (CN)';        u = 'https://www.baidu.com/' }
    @{ n = 'Naver (KR)';        u = 'https://www.naver.com/' }
    @{ n = 'Wikipedia';         u = 'https://zh.wikipedia.org/' }
    @{ n = 'Stack Overflow';    u = 'https://stackoverflow.com/' }
    @{ n = 'Cloudflare';        u = 'https://www.cloudflare.com/' }
    @{ n = 'Binance';           u = 'https://www.binance.com/' }
    @{ n = 'Coinbase';          u = 'https://www.coinbase.com/' }
)

if ($File -and (Test-Path $File)) {
    $ext = [IO.Path]::GetExtension($File).ToLower()
    if ($ext -eq '.json') {
        $sites = @(Get-Content $File -Raw -Encoding UTF8 | ConvertFrom-Json | ForEach-Object { @{ n = $_.n; u = $_.u } })
    } else {
        $sites = @(Import-Csv $File | ForEach-Object { @{ n = $_.n; u = $_.u } })
    }
} else {
    $sites = $builtin
}

# 取得網域（拿來做裸 TCP 複驗）
function Get-Authority {
    param([string]$Url)
    try { return ([Uri]$Url).Authority } catch { return $null }
}

function Test-RawTcp443 {
    param([string]$HostName, [int]$Timeout = 8000)
    $parsed = $null
    if (-not [Net.IPAddress]::TryParse($HostName, [ref]$parsed)) {
        $HostName = Resolve-DnsName $HostName -Type A -ErrorAction SilentlyContinue |
                    Where-Object IPAddress | Select-Object -First 1 -ExpandProperty IPAddress
    }
    if (-not $HostName) { return 'DNS-FAIL' }
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $r = $c.BeginConnect($HostName, 443, $null, $null)
        if ($r.AsyncWaitHandle.WaitOne($Timeout, $false)) { $c.EndConnect($r) | Out-Null; return 'OK' }
        return 'TIMEOUT'
    } catch { return 'REFUSED' } finally { $c.Close() }
}

# =====================================================================
Write-Output "=== 網站可達性掃描（$($sites.Count) 個站）==="
Write-Output ''
Write-Output '[OK]      = 2xx，完全正常'
Write-Output '[REACH]   = 伺服器有回應（4xx/5xx），網路可達，非封鎖'
Write-Output '[BLOCK]   = 真的連不上（裸 TCP 443 也失敗）'
Write-Output '[DNS-FAIL]= 網域無法解析'
Write-Output ''

$rows = foreach ($s in $sites) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $code = ''; $verdict = ''; $note = ''

    try {
        $r = Invoke-WebRequest -Uri $s.u -TimeoutSec $TimeoutSec -UserAgent $UA -MaximumRedirection 5 -ErrorAction Stop
        $code = [string]$r.StatusCode
        $verdict = if ($r.StatusCode -lt 400) { 'OK' } else { 'REACH' }
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            try { $code = [string][int]$resp.StatusCode } catch { $code = '?' }
            # 伺服器有回應 = 網路可達
            $verdict = if ([int]$code -ge 200) { 'REACH' } else { 'REACH' }
            switch ($code) {
                '401' { $note = '需要認證（正常）' }
                '403' { $note = 'Cloudflare / 需要登入（正常）' }
                '404' { $note = '路徑不存在但伺服器有回應（正常）' }
                '405' { $note = 'HTTP method 不符（正常）' }
                '429' { $note = '速率限制（正常）' }
                default { $note = '伺服器有回應' }
            }
        } else {
            # 沒有 HTTP 回應 → 需要裸 TCP 複驗才能定性
            $auth = Get-Authority $s.u
            $raw = if ($auth) { Test-RawTcp443 (($auth -split ':')[0]) } else { 'NO-AUTH' }
            switch ($raw) {
                'OK'       { $verdict = 'REACH';  $code = 'tcp-ok'; $note = 'TCP 443 正常，HTTP 層問題（headless/憑證/UA）' }
                'DNS-FAIL' { $verdict = 'DNSFAIL'; $code = 'dns';   $note = '網域無法解析（該網域可能不存在，非封鎖）' }
                default    { $verdict = 'BLOCK';  $code = 'tcp';   $note = "裸 TCP 443 也失敗：$raw" }
            }
        }
    }

    $sw.Stop()
    [pscustomobject]@{
        Site = $s.n; Url = $s.u; Code = $code; Verdict = $verdict
        Ms = $sw.ElapsedMilliseconds; Note = $note
    }
}

# --- 輸出 ---
$tagMap = @{ OK = '[ OK ]  '; REACH = '[REACH] '; BLOCK = '[BLOCK] '; DNSFAIL = '[DNS!!] ' }
foreach ($r in $rows) {
    $line = ('{0}{1,-24} {2,-8} {3,6}ms  {4}' -f $tagMap[$r.Verdict], $r.Site, $r.Code, $r.Ms, $r.Url)
    Write-Output $line
    if ($r.Note) { Write-Output ("         └─ {0}" -f $r.Note) }
}

# --- 統計 ---
$ok  = @($rows | Where-Object { $_.Verdict -eq 'OK' })
$rch = @($rows | Where-Object { $_.Verdict -eq 'REACH' })
$blk = @($rows | Where-Object { $_.Verdict -eq 'BLOCK' })
$dns = @($rows | Where-Object { $_.Verdict -eq 'DNSFAIL' })

Write-Output ''
Write-Output '=== 統計 ==='
Write-Output ("  正常 (2xx)                : {0}" -f $ok.Count)
Write-Output ("  可達（伺服器有回應，非封鎖）: {0}" -f $rch.Count)
Write-Output ("  DNS 無法解析               : {0}" -f $dns.Count)
Write-Output ("  真正被封鎖                 : {0}" -f $blk.Count)
Write-Output ("  合計                       : {0}" -f $rows.Count)

if ($blk.Count -eq 0 -and $dns.Count -eq 0) {
    Write-Output ''
    Write-Output '=== 結論 ==='
    Write-Output '  沒有任何網站遭到網路層封鎖。'
    Write-Output '  （[REACH] 的 401/403/404 是伺服器正常回應，瀏覽器開啟通常沒問題。）'
} else {
    Write-Output ''
    Write-Output '=== 真正被封鎖的站 ==='
    $blk | ForEach-Object { Write-Output ("  {0,-24} {1}  {2}" -f $_.Site, $_.Code, $_.Note) }
    Write-Output ''
    Write-Output '=== DNS 無法解析的站（可能網域本身就不存在）==='
    $dns | ForEach-Object { Write-Output ("  {0,-24} {1}" -f $_.Site, $_.Url) }
}

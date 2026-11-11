<#
.SYNOPSIS
    TLS 憑證簽發者檢查 — 偵測企業防火牆的 MITM / TLS 攔截。

.DESCRIPTION
    若公司有部署 SSL inspection，通常會在主機的「受信任的根憑證發行機」安裝
    自家 CA，此時網站憑證的 Issuer 會變成公司名稱。檢查簽發者即可判斷
    端對端加密是否被破解。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File test-tls.ps1
#>
[CmdletBinding()]
param([string[]]$Hosts = @())

$ErrorActionPreference = 'SilentlyContinue'

# `powershell -File x.ps1 -Hosts "a,b"` 會把整串當成單一元素，故自行再切一次
if ($Hosts) { $Hosts = @(($Hosts -join ',') -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }

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


if (-not $Hosts -or $Hosts.Count -eq 0) {
    $Hosts = @(
        'www.google.com', 'api.openai.com', 'api.anthropic.com', 'claude.ai',
        'github.com', 'raw.githubusercontent.com', 'registry.npmjs.org',
        'www.microsoft.com', 'fe2cr.update.microsoft.com',
        'huggingface.co', 'pypi.org', 'www.facebook.com'
    )
}

function Get-TlsIssuer {
    param([string]$HostName, [int]$Timeout = 10000)
    try {
        $client = New-Object System.Net.Sockets.TcpClient($HostName, 443)
        $ssl = New-Object System.Net.Security.SslStream($client.GetStream(), $false, ({ $true } -as [System.Net.Security.RemoteCertificateValidationCallback]))
        $ssl.ReadTimeout = $Timeout
        $ssl.WriteTimeout = $Timeout
        $ssl.AuthenticateAsClient($HostName)
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
        $result = [pscustomobject]@{
            Issuer  = $cert.Issuer
            Subject = $cert.Subject
            NotAfter = $cert.NotAfter
            Thumb   = $cert.Thumbprint
        }
        $ssl.Close(); $client.Close()
        return $result
    } catch {
        try { $client.Close() } catch {}
        return $null
    }
}

Write-Output '=== TLS 憑證簽發者檢查（MITM / 攔截偵測）==='
Write-Output ''

$rows = foreach ($h in $Hosts) {
    $c = Get-TlsIssuer $h
    if ($c) {
        [pscustomobject]@{ Host = $h; Ok = $true;  Issuer = $c.Issuer; Expires = $c.NotAfter }
    } else {
        [pscustomobject]@{ Host = $h; Ok = $false; Issuer = '(TLS 失敗)'; Expires = $null }
    }
}

# 已知第三方 CA 關鍵字（出現即為原廠憑證，非中間人）
$legitPatterns = @(
    "Google Trust Services", "Let's Encrypt", "ISRG", "DigiCert", "Sectigo",
    "Microsoft", "Amazon", "Apple", "Baltimore", "GlobalSign", "Entrust",
    "Comodo", "ZeroSSL", "GTS", "Cloudflare", "VeriSign", "Thawte", "GeoTrust"
)

$suspicious = @()

foreach ($r in $rows) {
    if (-not $r.Ok) {
        Write-Output ('  {0,-32} TLS HANDSHAKE FAILED' -f $r.Host)
        $suspicious += $r.Host
        continue
    }
    $isLegit = $false
    foreach ($p in $legitPatterns) {
        if ($r.Issuer -like "*$p*") { $isLegit = $true; break }
    }
    $flag = if ($isLegit) { '  ' } else { '<<' }
    $expiry = if ($r.Expires -and $r.Expires -gt (Get-Date)) { $r.Expires.ToString('yyyy-MM-dd') } else { 'EXPIRED' }
    Write-Output ('  {0} {1,-32} {2,-58} 到期 {3}' -f $flag, $r.Host, $r.Issuer, $expiry)
    if (-not $isLegit) { $suspicious += $r.Host }
}

Write-Output ''
Write-Output '=== 結論 ==='
Write-Output ''
if ($suspicious.Count -eq 0) {
    Write-Output '  所有憑證皆由已知第三方 CA 簽發，沒有企業 MITM 根憑證。'
    Write-Output '  => 端對端加密未被攔截，可正常使用。'
} else {
    Write-Output '  以下主機的簽發者不是已知第三方 CA，請人工確認是否為公司 SSL inspection：'
    $suspicious | ForEach-Object { Write-Output "      - $_" }
    Write-Output '  可用 certmgr.msc 檢查「受信任的根憑證發行機」是否有公司自簽 CA。'
}

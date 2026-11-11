<#
Local-only Telegram setup for the OpenCode usage monitor.

IMPORTANT: this file is intentionally ASCII-only. Windows PowerShell 5.1 reads
a .ps1 without a BOM using the system ANSI code page, which corrupts non-ASCII
string literals and can turn them into parser errors. Keep it English.

    powershell -ExecutionPolicy Bypass -File set_telegram.ps1
    powershell -ExecutionPolicy Bypass -File set_telegram.ps1 -Stdin
    powershell -ExecutionPolicy Bypass -File set_telegram.ps1 -Status
    powershell -ExecutionPolicy Bypass -File set_telegram.ps1 -Disable

Storage: %USERPROFILE%\.local\share\opencode-usage\telegram.enc
The bot token is stored DPAPI-encrypted (Windows user scope). The plaintext
never touches a config file, the snapshot, the dashboard, a log, or git.
#>
param(
  [string]$ChatId = '',
  [switch]$Disable,
  [switch]$Status,
  [switch]$Stdin
)

$ErrorActionPreference = 'Stop'
$dir  = Join-Path $env:USERPROFILE '.local\share\opencode-usage'
$file = Join-Path $dir 'telegram.enc'

function Read-DpapiToken {
  param([string]$Path)
  $j = Get-Content $Path -Raw | ConvertFrom-Json
  return (Unprotect-Base64 $j.token)
}

# DPAPI via the .NET API directly. Equivalent to ConvertFrom-SecureString but
# without depending on the Microsoft.PowerShell.Security module, which fails to
# autoload in some child-process contexts.
function Protect-Base64 {
  param([string]$Plain)
  Add-Type -AssemblyName System.Security
  $bytes = [Text.Encoding]::UTF8.GetBytes($Plain)
  $blob  = [Security.Cryptography.ProtectedData]::Protect(
    $bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
  return [Convert]::ToBase64String($blob)
}

function Unprotect-Base64 {
  param([string]$B64)
  Add-Type -AssemblyName System.Security
  $blob  = [Convert]::FromBase64String($B64)
  $bytes = [Security.Cryptography.ProtectedData]::Unprotect(
    $blob, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
  return [Text.Encoding]::UTF8.GetString($bytes)
}

if ($Status) {
  if (-not (Test-Path $file)) { Write-Host 'not configured'; exit 1 }
  $j = Get-Content $file -Raw | ConvertFrom-Json
  $t = Read-DpapiToken -Path $file
  Write-Host "enabled : $($j.enabled)"
  Write-Host "chat_id : $($j.chat_id)"
  Write-Host "token   : $($t.Substring(0,7))*$($t.Length) chars, DPAPI-encrypted"
  Write-Host "saved   : $($j.saved_at)"
  Write-Host "acl     : see icacls output below"
  exit 0
}

if ($Disable) {
  if (Test-Path $file) { Remove-Item $file -Force; Write-Host 'disabled, secret file removed' }
  else { Write-Host 'not configured' }
  exit 0
}

if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

if ($Stdin) {
  # Token arrives on stdin so it never appears in a process command line,
  # which any Get-Process / wmic on the machine could read.
  $plain = [Console]::In.ReadLine()
  $ChatId = [Console]::In.ReadLine()
  Write-Host 'token received via stdin'
}
else {
  Write-Host ''
  Write-Host '=== OpenCode usage - Telegram setup (local DPAPI encryption) ==='
  Write-Host ''
  Write-Host '1. Send /newbot to @BotFather to get a bot token'
  Write-Host '2. Open a chat with your bot and send /start'
  Write-Host '3. Open https://api.telegram.org/bot<TOKEN>/getUpdates and find the chat id'
  Write-Host ''
  $sec = Read-Host 'Bot Token (input is hidden)' -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  if (-not $ChatId) { $ChatId = Read-Host 'Chat ID' }
}

if ([string]::IsNullOrWhiteSpace($plain) -or $plain -notmatch '^\d+:[A-Za-z0-9_-]+$') {
  Write-Host 'invalid token format (expected 123456789:AAE...)' -ForegroundColor Red
  exit 1
}
if ([string]::IsNullOrWhiteSpace($ChatId)) {
  Write-Host 'chat id is required' -ForegroundColor Red
  exit 1
}

$sec = $null
if ($Stdin) { $sec = $null }

# encrypt first, then drop the plaintext from the variable
$enc = Protect-Base64 $plain
$plain = $null

$payload = [ordered]@{
  enabled  = $true
  token    = $enc
  chat_id  = $ChatId.Trim()
  saved_at = (Get-Date).ToString('s')
}
$payload | ConvertTo-Json | Set-Content -Path $file -Encoding UTF8

# restrict the ACL to the current user only
$me = "$env:USERDOMAIN\$env:USERNAME"
& icacls $file /inheritance:r /grant:r "${me}:(R,W)" 2>&1 | Out-Null

Write-Host ''
Write-Host "saved   : $file"
Write-Host "acl     : see icacls output below"
Write-Host "chat_id : $($payload.chat_id)"
Write-Host "token   : DPAPI-encrypted ($($enc.Length) chars), plaintext not written to disk"
Write-Host ''
Write-Host 'test with:  python ...\alert.py --test-telegram'

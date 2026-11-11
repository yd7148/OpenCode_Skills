<#
Registers a per-user (HKCU, no admin needed) URL protocol so the dashboard's
cleanup buttons can actually launch the local cleanup script:

    ocusage://safe
    ocusage://db
    ocusage://survey
    ocusage://purge?days=30

Run:   powershell -ExecutionPolicy Bypass -File register_protocol.ps1
Remove: powershell -ExecutionPolicy Bypass -File register_protocol.ps1 -Uninstall
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$skill = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'python not found on PATH' }
$cleanup = Join-Path $skill 'cleanup.py'
$key = 'HKCU:\Software\Classes\ocusage'

if ($Uninstall) {
  if (Test-Path $key) { Remove-Item -Recurse -Force $key }
  Write-Host 'ocusage:// handler removed'
  return
}

if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
New-ItemProperty -Path $key -Name '(Default)' -Value 'URL:OpenCode Usage' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null

$icon = Join-Path $skill 'dashboard-latest.html'
New-ItemProperty -Path $key -Name 'Icon' -Value $icon -PropertyType String -Force | Out-Null

$cmd = Join-Path $key 'shell\open\command'
if (-not (Test-Path $cmd)) { New-Item -Path $cmd -Force | Out-Null }
# output is teed to cleanup.log so the dashboard can show the result;
# 'purge' still refuses to run because the handler never passes --yes PURGE
$log = Join-Path $env:USERPROFILE '.local\share\opencode-usage\cleanup.log'
$handler = "cmd /c `"`"$py`" `"$cleanup`" `"%1`" --apply > `"$log`" 2>&1 & start `"`"$skill\dashboard-latest.html`"`""
New-ItemProperty -Path $cmd -Name '(Default)' -Value $handler -PropertyType String -Force | Out-Null

Write-Host 'registered HKCU\Software\Classes\ocusage'
Write-Host "  handler: $handler"
Write-Host ''
Write-Host 'test with:  Start-Process "ocusage://survey"'

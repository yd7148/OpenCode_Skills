<#
Registers two Windows Scheduled Tasks:
  - OpenCodeUsage-Collect : every 10 minutes, rebuilds the dashboard (zero resident memory)
  - OpenCodeUsage-Alert   : every 10 minutes, evaluates thresholds and fires notifications

Run:  powershell -ExecutionPolicy Bypass -File install_task.ps1
Remove: powershell -ExecutionPolicy Bypass -File install_task.ps1 -Uninstall
#>
param(
  [int]$IntervalMinutes = 10,
  [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$skill = Split-Path -Parent $MyInvocation.MyCommand.Path
$py   = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw 'python not found on PATH' }

if ($Uninstall) {
  'OpenCodeUsage-Collect', 'OpenCodeUsage-Alert' |
    ForEach-Object { Unregister-ScheduledTask -TaskName $_ -Confirm:$false -ErrorAction SilentlyContinue }
  Write-Host 'tasks removed'
  return
}

function New-OcTask($name, $script, $args_) {
  $cmd = "`"$py`" `"$script`" $args_"
  $a = New-ScheduledTaskAction -Execute $py -Argument "`"$script`" $args_" -WorkingDirectory $skill
  $t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
       -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
  $p = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
       -StartWhenAvailable -MultipleInstances IgnoreNew `
       -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
  Register-ScheduledTask -TaskName $name -Action $a -Trigger $t -Settings $p `
    -Description 'OpenCode usage monitor (read-only collector + dashboard + alerts)' `
    -Force | Out-Null
  Write-Host "registered $name  ->  $cmd"
}

New-OcTask 'OpenCodeUsage-Collect' (Join-Path $skill 'collect.py') ''
New-OcTask 'OpenCodeUsage-Alert'   (Join-Path $skill 'alert.py') '--quiet-ok'

Write-Host ''
Write-Host 'dashboard:'
Write-Host (Join-Path (Split-Path -Parent $skill) 'opencode-usage\dashboard-latest.html')
Get-ScheduledTask -TaskName 'OpenCodeUsage-*' |
  Select-Object TaskName, State | Format-Table -AutoSize

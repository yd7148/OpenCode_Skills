<#
.SYNOPSIS
    重建 mate-engine anim-patch 所需的工具鏈。

.DESCRIPTION
    Temp\opencode 下的工具會被系統 Temp 清理抹掉，必須能重建。
    這支腳本一次裝好：
      dnfile + dncil  (pip --target)
      UnityPy         (pip --target)
      Mono.Cecil      (NuGet .nupkg → lib\net40)
      PatchField.exe  (csc 編譯 scripts\PatchField.cs)

.NOTES
    执行后设置环境变量再跑 python：
      $env:MATE_TOOLS = "<ToolsRoot>"
#>
[CmdletBinding()]
param(
    [string]$ToolsRoot = (Join-Path $env:LOCALAPPDATA 'Temp\opencode'),
    [string]$Python    = 'python'
)

$ErrorActionPreference = 'Stop'

$dncilDir = Join-Path $ToolsRoot 'matedlltools'
$unityDir = Join-Path $ToolsRoot 'unitypy'
$cecilDir = Join-Path $ToolsRoot 'cecil'

foreach ($d in @($ToolsRoot, $dncilDir, $unityDir, $cecilDir)) {
    if (-not (Test-Path -LiteralPath $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

Write-Host '=== 1/4 pip: dnfile + dncil ===' -ForegroundColor Cyan
& $Python -m pip install --disable-pip-version-check --target=$dncilDir dnfile dncil
if ($LASTEXITCODE -ne 0) { throw 'dnfile/dncil 安裝失敗' }

Write-Host '=== 2/4 pip: UnityPy ===' -ForegroundColor Cyan
& $Python -m pip install --disable-pip-version-check --target=$unityDir UnityPy
if ($LASTEXITCODE -ne 0) { throw 'UnityPy 安裝失敗' }

# NuGet 的 .nupkg 其實就是 zip，但 Expand-Archive 只認 .zip 副檔名。
Write-Host '=== 3/4 Mono.Cecil (NuGet) ===' -ForegroundColor Cyan
$nupkg = Join-Path $cecilDir 'Mono.Cecil.nupkg'
$zip   = Join-Path $cecilDir 'Mono.Cecil.zip'
Invoke-WebRequest -Uri 'https://www.nuget.org/api/v2/package/Mono.Cecil/0.11.4' `
                  -OutFile $nupkg -UseBasicParsing
Copy-Item -LiteralPath $nupkg -Destination $zip -Force
$extract = Join-Path $cecilDir 'extract'
Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
Copy-Item -LiteralPath (Join-Path $extract 'lib\net40\Mono.Cecil.dll') `
          -Destination (Join-Path $cecilDir 'Mono.Cecil.dll') -Force
Write-Host "  Mono.Cecil.dll -> $(Join-Path $cecilDir 'Mono.Cecil.dll')"

Write-Host '=== 4/4 編譯 PatchField.exe ===' -ForegroundColor Cyan
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc)) { throw "找不到 csc: $csc" }

$src = Join-Path $PSScriptRoot 'PatchField.cs'
$exe = Join-Path $cecilDir 'PatchField.exe'
& $csc /nologo /target:exe /out:"$exe" /r:"$(Join-Path $cecilDir 'Mono.Cecil.dll')" "$src"
if ($LASTEXITCODE -ne 0) { throw 'PatchField.exe 編譯失敗' }
Write-Host "  PatchField.exe -> $exe"

Write-Host ''
Write-Host '=== 完成，套用方式 ===' -ForegroundColor Green
Write-Host "  `$env:MATE_TOOLS = '$ToolsRoot'"
Write-Host "  PatchField.exe <in.dll> <out.dll> totalIdleAnimations 19"
Write-Host "  PatchField.exe <stage1.dll> <stage2.dll> DANCE_CLIP_COUNT 13"

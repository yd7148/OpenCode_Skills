# Keeps a CPU-heavy background job under ~85-90% so the machine stays usable.
# - PriorityClass = BelowNormal (yields to interactive work)
# - ProcessorAffinity = 20 of 24 logical processors (4 logical cores reserved)
#
# GOTCHAS learned 2026-09-26:
#  * Do NOT filter by CommandLine. ProcessPoolExecutor workers have a CommandLine of
#    `python -c "from multiprocessing.spawn import spawn_main..."` with no reference to
#    the work folder, so a path filter misses them and they stay Normal -> 100% CPU.
#    Filter on CPU time instead: any python.exe that has burned CPU is part of the job.
#  * ProcessorAffinity is an IntPtr; `$_.ProcessorAffinity -ne $Mask` is ALWAYS true.
#    Compare as [int64] on both sides.
param([int]$Mask = 0x000FFFFF, [int]$MinCpuSeconds = 5)

while ($true) {
    Get-Process -Name python -ErrorAction SilentlyContinue |
        Where-Object { $_.CPU -gt $MinCpuSeconds } |
        ForEach-Object {
            try {
                if ($_.PriorityClass -ne "BelowNormal") { $_.PriorityClass = "BelowNormal" }
                if ([int64]$_.ProcessorAffinity -ne [int64]$Mask) { $_.ProcessorAffinity = $Mask }
            } catch {}
        }
    Start-Sleep -Seconds 15
}

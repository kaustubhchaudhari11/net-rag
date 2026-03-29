# Stops the process listening on a TCP port (e.g. 8000). Run in PowerShell:
#   .\scripts\stop_port.ps1 8000
param([Parameter(Mandatory = $true)][int] $Port)
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host "No LISTEN on port $Port"
    exit 0
}
$pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($p in $pids) {
    try {
        Stop-Process -Id $p -Force -ErrorAction Stop
        Write-Host "Stopped PID $p (was listening on $Port)"
    } catch {
        Write-Warning "Could not stop PID $p : $_"
    }
}

# Show what is using a TCP port (Windows). Usage: .\scripts\check_port.ps1 8000
param([Parameter(Mandatory = $true)][int] $Port)

Write-Host "=== netstat (port $Port) ===" -ForegroundColor Cyan
netstat -ano | findstr ":$Port "

Write-Host "`n=== LISTEN sockets + process ===" -ForegroundColor Cyan
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listen) {
    Write-Host "No LISTEN on port $Port"
    exit 0
}
foreach ($row in $listen | Select-Object -Property LocalAddress, LocalPort, OwningProcess -Unique) {
    $procId = $row.OwningProcess
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    Write-Host "PID $procId  Name: $($p.ProcessName)  Path: $($p.Path)"
    if (-not $p) {
        Write-Host "  (PID not found — often a stuck/zombie socket; reboot may be required)" -ForegroundColor Yellow
    }
}

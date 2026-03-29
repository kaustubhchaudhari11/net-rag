# Opens two PowerShell windows: FastAPI + Streamlit (8501), then your default browser.
# If port 8000 is held by a zombie socket, API automatically uses 8001 (same as manual uvicorn).
param([int] $ApiPort = 8000)
$here = $PSScriptRoot
$stop = Join-Path $here "scripts\stop_port.ps1"
if (Test-Path $stop) {
    & $stop $ApiPort
    Start-Sleep -Seconds 1
}

if ($ApiPort -eq 8000) {
    try {
        $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 8000)
        $l.Start()
        $l.Stop()
    } catch {
        Write-Warning "Port 8000 is not free — using API port 8001 for both windows."
        $ApiPort = 8001
        if (Test-Path $stop) {
            & $stop 8001
            Start-Sleep -Seconds 1
        }
    }
}
$apiScript = Join-Path $here "scripts\api_server.ps1"
$uiScript = Join-Path $here "scripts\ui_server.ps1"
Start-Process powershell -WorkingDirectory $here -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $apiScript, "-Port", "$ApiPort"
)
Start-Sleep -Seconds 6
Start-Process powershell -WorkingDirectory $here -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $uiScript, "-ApiPort", "$ApiPort"
)
Start-Sleep -Seconds 8
Start-Process "http://localhost:8501"
Write-Host ""
Write-Host "Started:"
Write-Host "  API:       http://127.0.0.1:$ApiPort/health"
Write-Host "  Streamlit: http://localhost:8501 (browser should open)"
Write-Host "Close each API/UI window with Ctrl+C when done."

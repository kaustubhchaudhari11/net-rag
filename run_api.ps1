# Default port 8000. Use Start-NetRAG.ps1 to launch API + UI + browser.
param([int] $Port = 8000)
$Root = $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "Missing $Py — create a venv and install the dependencies first."
    exit 1
}
Write-Host "Starting API from: $Root (port $Port)"
Write-Host "Health: http://127.0.0.1:$Port/health"
& $Py -m uvicorn app.api:app --reload --host 127.0.0.1 --port $Port --app-dir $Root

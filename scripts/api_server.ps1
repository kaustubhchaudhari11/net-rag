# API only — default port 8000 (must match NETRAG_API_BASE in .env / ui_server.ps1).
param([int] $Port = 8000)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py — create a venv and install the dependencies first."
    exit 1
}
Set-Location $root
Write-Host "Net-RAG API — http://127.0.0.1:$Port/health"
& $py -m uvicorn app.api:app --reload --host 127.0.0.1 --port $Port --app-dir $root

# Streamlit UI — points at API on $ApiPort (must match api_server.ps1).
param([int] $ApiPort = 8000)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py — create venv and install requirements first."
    exit 1
}
$env:NETRAG_API_BASE = "http://127.0.0.1:$ApiPort"
Set-Location $root
Write-Host "Streamlit — http://localhost:8501  (API: $env:NETRAG_API_BASE)"
& $py -m streamlit run app/ui.py

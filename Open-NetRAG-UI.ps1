# Open Streamlit in a new window when the API is already running (default: API on 8001).
param([int] $ApiPort = 8001)
$here = $PSScriptRoot
$ui = Join-Path $here "scripts\ui_server.ps1"
Start-Process powershell -WorkingDirectory $here -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $ui, "-ApiPort", "$ApiPort"
)
Start-Sleep -Seconds 8
Start-Process "http://localhost:8501"
Write-Host "Streamlit window opened. UI: http://localhost:8501  (API: http://127.0.0.1:$ApiPort)"

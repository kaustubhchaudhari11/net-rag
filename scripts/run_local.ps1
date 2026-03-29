# Net-RAG API — Terminal 1. Then in Terminal 2: .\scripts\run_ui.ps1
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing $py — run scripts\setup_local.bat or create .venv" }
# --app-dir fixes "No module named app" when cwd is wrong (e.g. .venv\Scripts)
& $py -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000 --app-dir $root


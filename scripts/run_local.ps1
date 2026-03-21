# Net-RAG API — Terminal 1: run from repo root after activating venv.
# Then in Terminal 2: .\scripts\run_ui.ps1
Set-Location (Join-Path $PSScriptRoot "..")
python -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000


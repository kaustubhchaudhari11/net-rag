# Streamlit — second terminal. API on 8000 (or set NETRAG_API_BASE / .env).
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$env:NETRAG_API_BASE = "http://127.0.0.1:8000"
$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -m streamlit run app/ui.py

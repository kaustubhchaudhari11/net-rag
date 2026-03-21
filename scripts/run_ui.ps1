# Net-RAG Streamlit UI — run from repo root in a second terminal (API must be up).
# Prerequisite: venv activated, `pip install -r requirements.txt`, `.env` from `.env.example`
Set-Location (Join-Path $PSScriptRoot "..")
streamlit run app/ui.py

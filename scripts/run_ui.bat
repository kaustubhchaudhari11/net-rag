@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Run scripts\setup_local.bat first to create .venv and install packages.
  pause
  exit /b 1
)
set NETRAG_API_BASE=http://127.0.0.1:8000
echo Starting Streamlit UI — API should be on %NETRAG_API_BASE%
echo Open http://localhost:8501 in your browser
".venv\Scripts\python.exe" -m streamlit run app/ui.py
pause

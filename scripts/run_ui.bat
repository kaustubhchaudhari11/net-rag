@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Run scripts\setup_local.bat first to create .venv and install packages.
  pause
  exit /b 1
)
echo Starting Streamlit UI ^(ensure API is running in another window^)
echo Open http://localhost:8501 in your browser
".venv\Scripts\python.exe" -m streamlit run app/ui.py
pause

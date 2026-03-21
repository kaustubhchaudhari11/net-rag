@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Run scripts\setup_local.bat first to create .venv and install packages.
  pause
  exit /b 1
)
echo Starting API at http://127.0.0.1:8000  ^(Ctrl+C to stop^)
".venv\Scripts\python.exe" -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
pause

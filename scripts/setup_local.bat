@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
echo.
echo Net-RAG local setup
echo Repository: %cd%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo During setup, enable "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
) else (
  echo Virtual environment .venv already exists.
)

echo.
echo Upgrading pip and installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install streamlit fastapi "uvicorn[standard]" langchain langchain-community faiss-cpu sentence-transformers pypdf python-dotenv requests python-multipart rank-bm25
if errorlevel 1 goto :fail

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo Created .env from .env.example ^(edit LLM_* if you want synthesis^)
) else (
  echo .env already exists ^(not overwritten^).
)

echo.
echo === Setup finished ===
echo Open TWO Command Prompt windows, both in this folder:
echo   cd /d "%cd%"
echo Then run:
echo   Window 1:  scripts\run_api.bat
echo   Window 2:  scripts\run_ui.bat
echo Browser: http://localhost:8501
echo.
pause
exit /b 0

:fail
echo [ERROR] pip install failed. See messages above.
pause
exit /b 1

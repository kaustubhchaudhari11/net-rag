# Net-RAG on Windows (without `Activate.ps1`)

PowerShell may show:

> running scripts is disabled on this system

**You do not need `Activate.ps1`.** Use **Command Prompt** (`cmd`) and the batch files in `scripts/`.

## One-time setup

1. Press **Win + R**, type `cmd`, Enter.
2. Run:

```bat
cd /d C:\Users\kaust\Documents\net-rag
scripts\setup_local.bat
```

This creates `.venv`, installs `requirements.txt`, and copies `.env.example` → `.env` if `.env` does not exist.

**Python not found?** Install Python 3.10+ from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH**, then open a new `cmd` and run the commands again.

## Run every time (two windows)

In **both** windows, go to the repo:

```bat
cd /d C:\Users\kaust\Documents\net-rag
```

- **Window 1:** `scripts\run_api.bat`  
- **Window 2:** `scripts\run_ui.bat`  

Then open **http://localhost:8501** — ingest docs from the sidebar, then ask questions.  
API health: **http://127.0.0.1:8000/health**

## Same steps without batch files

```bat
cd /d C:\Users\kaust\Documents\net-rag
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy /Y .env.example .env
```

API:

```bat
.venv\Scripts\python.exe -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

UI (second window):

```bat
.venv\Scripts\python.exe -m streamlit run app/ui.py
```

## Optional: fix PowerShell for `.ps1`

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then `.\.venv\Scripts\Activate.ps1` works if you prefer it.

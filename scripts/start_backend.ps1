$ErrorActionPreference = "Stop"
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000

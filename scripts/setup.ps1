# One-time setup. Run from the project root: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Push-Location frontend; npm install; Pop-Location
Write-Host "Setup complete. Next: scripts\train_sample.ps1, then scripts\start_backend.ps1 and scripts\start_frontend.ps1"

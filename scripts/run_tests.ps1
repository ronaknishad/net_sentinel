$ErrorActionPreference = "Stop"
& .\.venv\Scripts\python.exe -m pytest backend\tests -q
Push-Location frontend; npm test; npm run build; Pop-Location

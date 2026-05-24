$ErrorActionPreference = "Stop"

uv sync --extra build

uv run pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "CO2ControlApp" `
  --paths "src" `
  "run.py"

Write-Host "Executable build is available in dist\CO2ControlApp"

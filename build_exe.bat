@echo off
setlocal

uv sync --extra build
if errorlevel 1 exit /b %errorlevel%

uv run pyinstaller --noconfirm --clean --windowed --name CO2ControlApp --paths src run.py
if errorlevel 1 exit /b %errorlevel%

echo Executable build is available in dist\CO2ControlApp
pause

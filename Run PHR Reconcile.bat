@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "property_reconciliation\src\gui.py"
) else (
    echo Python virtual environment was not found at .venv\Scripts\python.exe
    echo Run Setup PHR Reconcile.bat before using this launcher.
    echo.
    pause
)

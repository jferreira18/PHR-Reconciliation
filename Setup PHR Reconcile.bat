@echo off
setlocal
cd /d "%~dp0"

echo Setting up PHR Reconcile...
echo.

py -3.11 --version
if errorlevel 1 (
    echo.
    echo Python 3.11 was not found.
    echo Install Python 3.11 or newer, then run this setup again.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

py -3.11 -m venv .venv
if errorlevel 1 (
    echo.
    echo Failed to create the virtual environment.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo.
echo Setup complete. You can now run:
echo Run PHR Reconcile.bat
pause

@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment was not found.
    echo Run Setup PHR Reconcile.bat first.
    pause
    exit /b 1
)

echo Installing PyInstaller...
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 (
    echo.
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo Building PHR Reconcile.exe...
set "PYTHON_ROOT="
for /f "usebackq delims=" %%i in (`".venv\Scripts\python.exe" -c "import sys; print(sys.base_prefix)"`) do set "PYTHON_ROOT=%%i"
set "TCL_LIBRARY=%PYTHON_ROOT%\tcl\tcl8.6"
set "TK_LIBRARY=%PYTHON_ROOT%\tcl\tk8.6"

".venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "PHR Reconcile" ^
  --paths "property_reconciliation\src" ^
  --workpath "build_exe" ^
  --distpath "release" ^
  --add-data "%PYTHON_ROOT%\tcl\tcl8.6;tcl\tcl8.6" ^
  --add-data "%PYTHON_ROOT%\tcl\tk8.6;tcl\tk8.6" ^
  "property_reconciliation\src\gui.py"

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete:
echo release\PHR Reconcile.exe
pause

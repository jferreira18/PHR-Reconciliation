$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onefile `
  --name "PHRDiff" `
  phr_diff_gui.py

Write-Host ""
Write-Host "Built executable: dist\PHRDiff.exe"

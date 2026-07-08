import sys
from pathlib import Path
import re
import pandas as pd

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "PHR CAO 07JUL.XLSX"
if not path.exists():
    print(f"File not found: {path}")
    sys.exit(1)

print(f"Inspecting: {path}\n")
df = pd.read_excel(path)
print("Columns:", list(df.columns))

serial_like = re.compile(r"[A-Za-z0-9\-]{3,}")
examples = {}
for col in df.columns:
    vals = df[col].dropna().astype(str)
    sample = []
    for v in vals.head(200):
        if re.search(r"\d", v) and len(v.strip()) >= 3:
            sample.append(v.strip())
        if len(sample) >= 10:
            break
    if sample:
        examples[col] = sample

if not examples:
    print("No serial-like examples found in the first 200 rows of any column.")
else:
    for col, vals in examples.items():
        print(f"\nColumn: {col}")
        for v in vals:
            print(" ", v)

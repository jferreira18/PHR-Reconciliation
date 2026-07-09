# PHR to PSD Reconciliation

This tool builds a single unit-level reconciliation CSV from uploaded Army property files. Each PHR item is expanded to one row per unit, then matching PSD information is appended to that same row.

## What Users Need
For each run, the user needs:

- PHR PDF
- PHR XLSX export
- PSD PULL workbook

The Divestment Tracker is not part of the normal user workflow.

## First-Time Setup
If you received `PHR Reconcile.exe`, skip this section and use `Packaged EXE Run`.

1. Download this project folder, or download the repository ZIP and extract it.
2. Install Python 3.11 or newer from `https://www.python.org/downloads/`.
3. Open the extracted project folder.
4. Double-click `Setup PHR Reconcile.bat`.
5. Wait for the setup window to say `Setup complete`.

The setup creates `.venv` and installs the Python packages from `requirements.txt`.

## Packaged EXE Run
Use this when deploying to someone who should not install Python.

1. Send the user `release\PHR Reconcile.exe`.
2. The user double-clicks `PHR Reconcile.exe`.
3. In the GUI, choose the three source files:
   - PHR PDF
   - PHR XLSX export
   - PSD PULL workbook
4. Click `Run`.
5. When the run completes, click `Open CSV` or `Open Output Folder`.

## Source Folder Run
Use this when running from the project folder during development.

1. Double-click `Run PHR Reconcile.bat`.
2. In the GUI, choose the three source files:
   - PHR PDF
   - PHR XLSX export
   - PSD PULL workbook
3. Click `Run`.
4. When the run completes, click `Open CSV` or `Open Output Folder`.

The final output is:

- `property_reconciliation/outputs/phr_table_with_psd.csv`

## If Something Fails
The GUI displays run output and error details in the log area.

If a user needs to report an issue:

1. Leave the GUI open after the failure.
2. Click `Copy Log`.
3. Send the copied text with the three source file names used for the run.

The log includes unit-test failures, file-reading errors, parser errors, and the Python traceback needed for troubleshooting.

## Output Fields
The final CSV contains the normalized PHR unit rows plus appended PSD fields:

- `page`, `lin`, `nsn`, `nomenclature`, `quantity`, `serial_number`
- `psd_match_status`, `psd_match_method`, `psd_psd_id`
- `psd_from_code`, `psd_to_code`, `psd_from_name`, `psd_to_name`
- `psd_to_pb_lin`, `psd_source_niin`, `psd_source_lin_name`
- `psd_validated_quantity`, `psd_psd_status`, `psd_condition_maintenance`
- `psd_serial_numbers`, `psd_type`, `psd_vetting_level`, `psd_vetting_status`
- `psd_status`, `psd_erds_pass_thru?`

## Matching Rules
The PHR PDF is parsed into unit-level rows. If a PHR line has quantity greater than one and no serial numbers, duplicate rows are expected.

PSD matching is deterministic:

1. Serial + identifier + LIN
2. Serial + identifier
3. Identifier + LIN
4. Identifier only
5. `missing_psd` when no corresponding PSD is found

Serial-only matches are intentionally avoided because short serial values can collide across unrelated PSDs.

## Validation
The PHR XLSX is used as a validation reference. Its `Stock` column is the authoritative expansion quantity for the current export shape; `ZPBBOM QTY` is not used for unit expansion.

The app runs unit tests before producing output. If tests fail, the output is not regenerated and the GUI log shows the failure.

## Build The EXE
Use this when you need to create a fresh no-Python deployment build.

1. Complete `First-Time Setup`.
2. Double-click `Build EXE.bat`.
3. Send the generated file:

```text
release\PHR Reconcile.exe
```

## CLI Troubleshooting
From the repository root:

```powershell
.\.venv\Scripts\python.exe property_reconciliation\src\run_pipeline.py `
  --phr-pdf "path\to\phr.pdf" `
  --phr-xlsx "path\to\phr.xlsx" `
  --psd-xlsx "path\to\psd_pull.xlsx"
```

Run tests manually with:

```powershell
.\.venv\Scripts\python.exe -m unittest -v property_reconciliation\src\test_parse_phr_table.py property_reconciliation\src\test_reconcile_psd.py
```

# PHR Reconciliation

This repository now contains two separate local tools for Primary Hand Receipt work:

1. `property_reconciliation`: reconciles one PHR against a PSD PULL workbook and produces a CSV.
2. `PHRDiff`: compares two PHR PDFs and produces a GitHub-style visual split-diff report plus a printable side-by-side PDF report.

The tools are related, but their processes stay separate. Use `property_reconciliation` when you need the PSD reconciliation CSV. Use `PHRDiff` when you need to compare two PHR PDFs against each other.

## Tool 1: PHR To PSD Reconciliation

This is the original workflow. It builds a single unit-level reconciliation CSV from uploaded Army property files. Each PHR item is expanded to one row per unit, then matching PSD information is appended to that same row.

### What Users Need

For each run, the user needs:

- PHR PDF
- PHR XLSX export
- PSD PULL workbook

The Divestment Tracker is not part of the normal user workflow.

### Packaged EXE Run

Use this when deploying to someone who should not install Python.

1. Send the user `release\PHR Reconcile.exe`.
2. The user double-clicks `PHR Reconcile.exe`.
3. In the GUI, choose the three source files:
   - PHR PDF
   - PHR XLSX export
   - PSD PULL workbook
4. Click `Run`.
5. When the run completes, click `Open CSV` or `Open Output Folder`.

### Source Folder Run

Use this when running from the project folder during development.

1. Double-click `Run PHR Reconcile.bat`.
2. In the GUI, choose the three source files:
   - PHR PDF
   - PHR XLSX export
   - PSD PULL workbook
3. Click `Run`.
4. When the run completes, click `Open CSV` or `Open Output Folder`.

The final output is:

```text
property_reconciliation/outputs/phr_table_with_psd.csv
```

### Output Fields

The final CSV contains the normalized PHR unit rows plus appended PSD fields:

- `page`, `lin`, `nsn`, `nomenclature`, `quantity`, `serial_number`
- `psd_match_status`, `psd_match_method`, `psd_psd_id`
- `psd_from_code`, `psd_to_code`, `psd_from_name`, `psd_to_name`
- `psd_to_pb_lin`, `psd_source_niin`, `psd_source_lin_name`
- `psd_validated_quantity`, `psd_psd_status`, `psd_condition_maintenance`
- `psd_serial_numbers`, `psd_type`, `psd_vetting_level`, `psd_vetting_status`
- `psd_status`, `psd_erds_pass_thru?`

### Matching Rules

The PHR PDF is parsed into unit-level rows. If a PHR line has quantity greater than one and no serial numbers, duplicate rows are expected.

PSD matching is deterministic:

1. Serial + identifier + LIN
2. Serial + identifier
3. Identifier + LIN
4. Identifier only
5. `missing_psd` when no corresponding PSD is found

Serial-only matches are intentionally avoided because short serial values can collide across unrelated PSDs.

### Validation

The PHR XLSX is used as a validation reference. Its `Stock` column is the authoritative expansion quantity for the current export shape; `ZPBBOM QTY` is not used for unit expansion.

The app runs unit tests before producing output. If tests fail, the output is not regenerated and the GUI log shows the failure.

## Tool 2: PHR Diff

`PHRDiff` is a separate subproject located at:

```text
PHRDiff\
```

It compares two GCSS-Army Primary Hand Receipt PDFs semantically and creates a local visual split-diff report. This is useful for answering questions like:

- What items were added between two PHRs?
- What quantities changed?
- Were serial numbers added or removed?
- Which validation warnings need review?

The HTML report looks like a GitHub-style split diff, with baseline records on the left and current records on the right. PHR Diff also writes `phr-diff-report.pdf`, a printable side-by-side PDF with the baseline page on the left, the current page on the right, and the same highlights painted into the PDF.

![PHR Diff visual report](PHRDiff/docs/screenshots/visual-report-main.png)

### PHR Diff Inputs

For each PHR Diff run, the user needs:

- baseline PHR PDF
- current PHR PDF

This workflow does not require the PSD PULL workbook or PHR XLSX export.

### PHR Diff Packaged EXE Run

Use this when deploying to someone who should not install Python.

1. Open:

```text
PHRDiff\dist\PHRDiff.exe
```

2. Choose the baseline PDF.
3. Choose the current PDF.
4. Enter a report folder name.
5. Optionally enable metadata-only changes or full-page rendering.
6. Click `Generate Report`.
7. Open the generated visual report link or the PDF report link.

The PHR Diff executable opens a local browser-based upload screen. It does not send files to an external site; the browser page is only a local interface for selecting PDFs.

![PHR Diff upload screen](PHRDiff/docs/screenshots/gui-upload.png)

PHR Diff reports are written under:

```text
Downloads\PHR Diff Reports
```

### PHR Diff Source Run

From the `PHRDiff` subfolder:

```powershell
pip install -r requirements.txt
python -m phr_diff OLD.pdf NEW.pdf
```

For the included development fixtures:

```powershell
python -m phr_diff fixtures/WACEHD_PHR_JULY.pdf fixtures/"WACEHD PHR AUG.pdf"
```

### PHR Diff README

PHR Diff keeps its own detailed README, including screenshots, build instructions, warning tags, architecture, and tests:

```text
PHRDiff\README.md
```

Keep that README with the subproject. The parent README only summarizes how PHR Diff fits into the larger PHR Reconciliation folder.

## Which Tool Should I Use?

Use `PHR Reconcile` when:

- you have one PHR and one PSD PULL workbook
- you need a CSV showing PHR rows with appended PSD match fields
- you need deterministic PSD matching status

Use `PHRDiff` when:

- you have two PHR PDFs
- you need to see what changed between the old and new receipt
- you want an interactive visual report, a printable side-by-side PDF report, and tagged warnings

## First-Time Setup For Source Runs

If you received packaged executables, skip this section.

1. Install Python 3.11 or newer from `https://www.python.org/downloads/`.
2. Open the project folder.
3. Double-click `Setup PHR Reconcile.bat` for the original PSD reconciliation workflow.
4. For PHR Diff source runs, open `PHRDiff\` and run:

```powershell
pip install -r requirements.txt
```

Each tool owns its own dependencies and run commands.

## Build The EXEs

### Build PHR Reconcile

From the repository root:

```text
Build EXE.bat
```

The output is:

```text
release\PHR Reconcile.exe
```

### Build PHR Diff

From the `PHRDiff` subfolder:

```powershell
.\build_exe.ps1
```

The output is:

```text
PHRDiff\dist\PHRDiff.exe
```

## Troubleshooting

### PHR Reconcile Failure

The PHR Reconcile GUI displays run output and error details in the log area.

If a user needs to report an issue:

1. Leave the GUI open after the failure.
2. Click `Copy Log`.
3. Send the copied text with the three source file names used for the run.

### PHR Diff Warning Or Failure

PHR Diff reports validation warnings with tags such as:

- `SERIAL COUNT`
- `LOT QTY`
- `DUPLICATE STOCK`
- `DUPLICATE SERIAL`
- `COORDINATE`
- `VISUAL BOX`
- `PARSER`
- `VALIDATION`

When the `Warnings` filter is selected, the left sidebar switches from change entries to warning entries. Each warning can be selected independently and includes a short explanation.

![PHR Diff tagged warnings](PHRDiff/docs/screenshots/visual-report-warnings.png)

Open `PHRDiff\README.md` for detailed warning explanations.

## CLI Troubleshooting

### PHR Reconcile CLI

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

### PHR Diff CLI

From the `PHRDiff` subfolder:

```powershell
pytest
python -m phr_diff OLD.pdf NEW.pdf --output phr_report --no-open
```

## Data Handling

Both tools are local-first:

- Source files remain on the user's computer.
- No telemetry is sent.
- No external services are called.
- PHR Diff's browser GUI runs on `127.0.0.1` only.

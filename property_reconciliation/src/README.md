# Source Notes

The normal user entry point is `../../Run PHR Reconcile.bat`.

## Modules
- `gui.py`: provides the Windows file-picker interface used by `../../Run PHR Reconcile.bat`.
- `parse_phr_table.py`: parses the uploaded PHR PDF into unit-level PHR rows.
- `reconcile_psd.py`: appends matching PSD fields from the PSD PULL workbook.
- `run_pipeline.py`: runs tests, builds the final output, and writes `../outputs/phr_table_with_psd.csv`.
- `test_parse_phr_table.py`: parser regression tests.
- `test_reconcile_psd.py`: PSD matching regression tests.

## Workflow
1. Upload/provide a PHR PDF, PHR XLSX, and PSD PULL workbook.
2. Double-click `Run PHR Reconcile.bat`, or run `run_pipeline.py` with those paths for CLI troubleshooting.
3. Review `../outputs/phr_table_with_psd.csv`.
4. If the GUI shows an error, click `Copy Log` and send the copied text for troubleshooting.

Intermediate normalized tables are kept in memory during normal runs. The final CSV is the visible output.

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

import pandas as pd

from parse_phr_table import PHRTableParser
from reconcile_psd import append_psd_matches, load_psd_rows


DEFAULT_OUTPUT = Path("property_reconciliation") / "outputs" / "phr_table_with_psd.csv"


def run_unit_tests() -> None:
    import test_parse_phr_table
    import test_reconcile_psd

    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_parse_phr_table))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_reconcile_psd))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("Unit tests failed. Output was not regenerated.")


def summarize_phr_workbook(path: Path) -> tuple[int, int]:
    df = pd.read_excel(path, sheet_name="Sheet1", dtype=str)
    stock = pd.to_numeric(df.get("Stock"), errors="coerce").fillna(0).astype(int)
    material_rows = df.get("Material", pd.Series(dtype=str)).notna().sum()
    return int(material_rows), int(stock.sum())


def build_output(
    phr_pdf: Path,
    phr_xlsx: Path,
    psd_xlsx: Path,
    output_path: Path,
) -> pd.DataFrame:
    parser = PHRTableParser(str(phr_pdf))
    phr_rows = parser.parse()

    workbook_rows, workbook_units = summarize_phr_workbook(phr_xlsx)
    if len(phr_rows) != workbook_units:
        print(
            "Warning: parsed PHR unit rows do not match PHR XLSX Stock total "
            f"({len(phr_rows)} parsed vs {workbook_units} workbook units).",
            file=sys.stderr,
        )

    psd_rows = load_psd_rows(psd_xlsx)
    output = append_psd_matches(phr_rows, psd_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)

    matched = int((output["psd_match_status"] == "matched").sum())
    print(f"PHR XLSX line rows: {workbook_rows}")
    print(f"PHR XLSX Stock total: {workbook_units}")
    print(f"PHR PDF unit rows parsed: {len(phr_rows)}")
    print(f"PSD source rows loaded: {len(psd_rows)}")
    print(f"PSD matched rows: {matched}")
    print(f"PSD missing rows: {len(output) - matched}")
    print(f"Final output: {output_path}")

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the PHR unit-level reconciliation output with PSD fields appended."
    )
    parser.add_argument("--phr-pdf", required=True, type=Path, help="Path to the uploaded PHR PDF.")
    parser.add_argument("--phr-xlsx", required=True, type=Path, help="Path to the uploaded PHR XLSX.")
    parser.add_argument(
        "--psd-xlsx",
        required=True,
        type=Path,
        help="Path to the uploaded PSD PULL workbook.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output CSV path. Defaults to property_reconciliation/outputs/phr_table_with_psd.csv.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the unit-test gate before running the pipeline.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_tests:
        print("Running unit tests...", flush=True)
        run_unit_tests()

    build_output(
        phr_pdf=args.phr_pdf,
        phr_xlsx=args.phr_xlsx,
        psd_xlsx=args.psd_xlsx,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

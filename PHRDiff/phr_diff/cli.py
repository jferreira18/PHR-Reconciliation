from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

from .compare import compare_receipts
from .parser import parse_hand_receipt
from .report import generate_report, summary
from .validation import attach_validation_warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Git-style visual diff for two GCSS-Army PHR PDFs.")
    parser.add_argument("old_pdf", type=Path)
    parser.add_argument("new_pdf", type=Path)
    parser.add_argument("--output", type=Path, default=Path("phr_report"))
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--include-metadata-changes", action="store_true")
    parser.add_argument("--full-pages", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    old_pdf = args.old_pdf
    new_pdf = args.new_pdf

    print("Parsing baseline PHR...")
    old_receipt = parse_hand_receipt(old_pdf)
    print("Parsing current PHR...")
    new_receipt = parse_hand_receipt(new_pdf)

    reconciliation = compare_receipts(old_receipt, new_receipt, include_metadata_changes=args.include_metadata_changes)
    attach_validation_warnings(reconciliation, old_receipt, new_receipt)

    args.output.mkdir(parents=True, exist_ok=True)
    if args.json_only:
        json_path = args.output / "reconciliation.json"
        json_path.write_text(
            json.dumps(
                {
                    "summary": summary(reconciliation),
                    "warnings": reconciliation.warnings,
                    "changes": [change.__dict__ for change in reconciliation.changes],
                },
                default=lambda o: o.__dict__,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"JSON report: {json_path}")
        return 0

    index = generate_report(
        old_pdf,
        new_pdf,
        old_receipt,
        new_receipt,
        reconciliation,
        args.output,
        full_pages=args.full_pages,
    )

    stats = summary(reconciliation)
    print(f"Baseline records: {stats['baseline_records']}")
    print(f"Current records: {stats['current_records']}")
    print(f"Detected changes: {stats['changes']}")
    print(f"Validation warnings: {stats['validation_warnings']}")
    print(f"Visual report: {index}")

    if args.debug and reconciliation.warnings:
        print("Warnings:")
        for warning in reconciliation.warnings:
            print(f"  - {warning}")

    if not args.no_open:
        webbrowser.open(index.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


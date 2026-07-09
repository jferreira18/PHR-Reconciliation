from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd

PSD_COLUMNS_TO_APPEND = [
    "PSD ID",
    "From Code",
    "To Code",
    "From Name",
    "To Name",
    "To PB LIN",
    "Source NIIN",
    "Source LIN Name",
    "Validated Quantity",
    "PSD Status",
    "Condition/Maintenance",
    "Serial Numbers",
    "Type",
    "Vetting Level",
    "Vetting Status",
    "Status",
    "ERDS Pass thru?",
]


def normalize_identifier(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip().upper()
    if not text or text in {"N/A", "NA", "NONE", "NAN"}:
        return ""

    text = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d+(?:\.0)?", text):
        digits = re.sub(r"\D", "", text)
        if len(digits) > 9:
            digits = digits[-9:]
        return digits.zfill(9)

    return re.sub(r"[^A-Z0-9:_\-]", "", text)


def identifier_keys(value: object) -> set[str]:
    normalized = normalize_identifier(value)
    if not normalized:
        return set()

    keys = {normalized}
    if re.fullmatch(r"\d{4}[A-Z0-9:_\-]+", normalized):
        keys.add(normalized[4:])
    return keys


def normalize_optional(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip().upper()
    if text in {"", "N/A", "NA", "NONE", "NAN"}:
        return ""
    return text


def normalize_serial(value: object) -> str:
    text = normalize_optional(value)
    if not text:
        return ""

    text = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d+", text):
        text = text.lstrip("0") or "0"
    return text


def split_psd_serials(value: object) -> set[str]:
    text = normalize_optional(value)
    if not text:
        return set()

    text = re.sub(r"^\(\s*\d+\s*\)\s*", "", text)
    parts = re.split(r"[,;\n\r]+", text)
    serials = {normalize_serial(part) for part in parts}
    return {serial for serial in serials if serial}


def to_int(value: object) -> int:
    if pd.isna(value):
        return 0

    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else 0


def load_psd_rows(path: Path) -> pd.DataFrame:
    with pd.ExcelFile(path) as workbook:
        if "POWER BI" in workbook.sheet_names:
            df = pd.read_excel(workbook, sheet_name="POWER BI", dtype=str)
        elif "PSD Pull" in workbook.sheet_names:
            df = pd.read_excel(workbook, sheet_name="PSD Pull", dtype=str, header=1)
        else:
            raise ValueError(
                f"No PSD source sheet found in {path}. Expected 'POWER BI' or 'PSD Pull'."
            )

    df = df.copy()
    required_columns = set(PSD_COLUMNS_TO_APPEND)
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"PSD source is missing required columns: {missing_columns}")

    df["_validated_quantity_int"] = df["Validated Quantity"].map(to_int)
    df["_serial_set"] = df["Serial Numbers"].map(split_psd_serials)
    df["_identifier_keys"] = df["Source NIIN"].map(identifier_keys)
    df["_lin_norm"] = df["To PB LIN"].map(normalize_optional)
    return df


def build_indexes(psd_df: pd.DataFrame) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    by_serial: dict[str, list[int]] = defaultdict(list)
    by_identifier: dict[str, list[int]] = defaultdict(list)

    for idx, row in psd_df.iterrows():
        for serial in row["_serial_set"]:
            by_serial[serial].append(idx)
        for key in row["_identifier_keys"]:
            by_identifier[key].append(idx)

    return by_serial, by_identifier


def choose_psd(
    candidates: Iterable[int],
    psd_df: pd.DataFrame,
    phr_lin: str,
    usage: dict[int, int],
) -> tuple[int | None, str]:
    candidate_list = list(candidates)
    if not candidate_list:
        return None, ""

    def score(idx: int) -> tuple[int, int, str]:
        row = psd_df.loc[idx]
        lin_score = 0 if phr_lin and row["_lin_norm"] == phr_lin else 1
        capacity = row["_validated_quantity_int"] or 1
        capacity_score = 0 if usage[idx] < capacity else 1
        return (lin_score, capacity_score, str(row.get("PSD ID", "")))

    chosen = sorted(candidate_list, key=score)[0]
    row = psd_df.loc[chosen]
    if phr_lin and row["_lin_norm"] == phr_lin:
        return chosen, "identifier_lin"
    return chosen, "identifier"


def append_psd_matches(phr_df: pd.DataFrame, psd_df: pd.DataFrame) -> pd.DataFrame:
    by_serial, by_identifier = build_indexes(psd_df)
    usage: dict[int, int] = defaultdict(int)

    matched_rows = []
    for _, phr_row in phr_df.iterrows():
        phr_identifier_keys = identifier_keys(phr_row.get("nsn"))
        phr_serial = normalize_serial(phr_row.get("serial_number"))
        phr_lin = normalize_optional(phr_row.get("lin"))

        match_idx: int | None = None
        match_method = ""
        identifier_candidates: list[int] = []
        seen = set()
        for key in phr_identifier_keys:
            for idx in by_identifier.get(key, []):
                if idx not in seen:
                    seen.add(idx)
                    identifier_candidates.append(idx)

        if phr_serial:
            serial_candidates = by_serial.get(phr_serial, [])
            serial_identifier_candidates = [
                idx for idx in serial_candidates if idx in set(identifier_candidates)
            ]
            if serial_identifier_candidates:
                match_idx, match_method = choose_psd(serial_identifier_candidates, psd_df, phr_lin, usage)
                if match_method:
                    match_method = "serial_" + match_method

        if match_idx is None:
            match_idx, match_method = choose_psd(identifier_candidates, psd_df, phr_lin, usage)

        output_row = phr_row.to_dict()
        if match_idx is None:
            output_row["psd_match_status"] = "missing_psd"
            output_row["psd_match_method"] = ""
            for column in PSD_COLUMNS_TO_APPEND:
                output_row[f"psd_{column.lower().replace(' ', '_').replace('/', '_')}"] = ""
        else:
            usage[match_idx] += 1
            psd_row = psd_df.loc[match_idx]
            output_row["psd_match_status"] = "matched"
            output_row["psd_match_method"] = match_method
            for column in PSD_COLUMNS_TO_APPEND:
                output_row[f"psd_{column.lower().replace(' ', '_').replace('/', '_')}"] = psd_row.get(column, "")

        matched_rows.append(output_row)

    return pd.DataFrame(matched_rows)


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Append PSD fields to an existing PHR unit CSV.")
    arg_parser.add_argument("--phr-table", required=True, type=Path, help="Path to a PHR unit CSV.")
    arg_parser.add_argument(
        "--psd-xlsx",
        required=True,
        type=Path,
        help="Path to a PSD PULL workbook.",
    )
    arg_parser.add_argument("--output", required=True, type=Path, help="Output CSV path.")
    args = arg_parser.parse_args()

    phr_df = pd.read_csv(args.phr_table, dtype=str)
    psd_df = load_psd_rows(args.psd_xlsx)
    reconciled = append_psd_matches(phr_df, psd_df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    reconciled.to_csv(args.output, index=False)

    matched = (reconciled["psd_match_status"] == "matched").sum()
    print(f"PHR rows: {len(reconciled)}")
    print(f"Matched PSD rows: {matched}")
    print(f"Missing PSD rows: {len(reconciled) - matched}")
    print(f"Saved {args.output}")
    print(reconciled.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

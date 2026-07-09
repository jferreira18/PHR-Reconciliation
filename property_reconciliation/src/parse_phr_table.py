from __future__ import annotations

import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pdfplumber


class PHRTableParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def parse(self) -> pd.DataFrame:
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        records: List[Dict[str, object]] = []
        # LINs are expected to be 6-character alphanumeric codes such as D17191, NA155H, or 70210N.
        lin_pattern = re.compile(r"\b[A-Z0-9]{6}\b")
        pending_serials: List[str] = []
        current_record: Optional[Dict[str, object]] = None
        last_lin: Optional[str] = None
        lookback: List[str] = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                for line in lines:
                    if self._is_header_line(line):
                        continue

                    item_match = self._match_item_line(line)
                    if item_match:
                        if current_record is not None:
                            current_record["serial_numbers"] = self._join_serials(pending_serials)
                            records.append(current_record)

                        found_lin = last_lin
                        if not found_lin:
                            for prev in reversed(lookback[-6:]):
                                prev_stripped = prev.strip()
                                if re.fullmatch(r"[A-Z0-9]{6}", prev_stripped.upper()):
                                    found_lin = prev_stripped.upper()
                                    break

                        current_record = {
                            "page": page_number,
                            "lin": found_lin,
                            "nsn": item_match["nsn"],
                            "nomenclature": item_match["nomenclature"],
                            "quantity": int(item_match["quantity"]),
                            "serial_numbers": None,
                        }
                        pending_serials = []
                        last_lin = None
                        lookback.append(line)
                        continue

                    if self._is_mpo_line(line):
                        last_lin = self._extract_lin(line)
                        lookback.append(line)
                        continue

                    if current_record is not None:
                        serials = self._extract_serial_candidates(
                            line,
                            allow_lin_like=True,
                            allow_short_numeric=True,
                        )
                        if serials:
                            pending_serials.extend(serials)

                    elif lin_pattern.search(line):
                        last_lin = self._extract_lin(line)

                    lookback.append(line)

        if current_record is not None:
            current_record["serial_numbers"] = self._join_serials(pending_serials)
            records.append(current_record)

        if not records:
            return pd.DataFrame(columns=["page", "lin", "nsn", "nomenclature", "quantity", "serial_numbers"])

        df = pd.DataFrame(records)
        df = df.reset_index(drop=True)
        # expand quantities into single-unit rows and assign serials when available
        df_expanded = self._expand_quantities(df)
        return df_expanded

    def save_csv(self, output_path: str) -> pd.DataFrame:
        df = self.parse()
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        return df

    def _is_header_line(self, line: str) -> bool:
        line_lower = line.lower()
        header_markers = [
            "primary hand receipt",
            "date:",
            "time:",
            "page ",
            "fe:",
            "uic:",
            "mpo mpo description",
            "nsn nsn description",
            "sysno serno",
            "serial number",
            "ui ciic dla buom oh qty",
        ]
        return any(marker in line_lower for marker in header_markers)

    def _match_item_line(self, line: str) -> Optional[Dict[str, str]]:
        line = self._separate_attached_description(line)
        pattern = re.compile(
            r"^(?P<nsn>[A-Z0-9:_\-]{6,})\s+(?P<nomenclature>.+?)\s+(?P<ui>\S+)\s+(?P<ciic>\S+)\s+(?P<dla>\S+)\s+(?P<uom>\S+)\s+(?P<quantity>\d+)$",
            re.I,
        )
        match = pattern.match(line)
        if not match:
            return None

        nsn = self._normalize_nsn(match.group("nsn"))
        return {
            "nsn": nsn,
            "nomenclature": match.group("nomenclature").strip(),
            "quantity": match.group("quantity"),
        }

    def _separate_attached_description(self, line: str) -> str:
        match = re.match(r"^(\d{4}[A-Z0-9]+:[A-Z0-9_]+?)([A-Z][a-z].*)$", line)
        if not match:
            return line
        return f"{match.group(1)} {match.group(2)}"

    def _normalize_nsn(self, nsn: str) -> str:
        value = str(nsn).strip().upper()
        if not value:
            return ""

        if re.fullmatch(r"\d+", value):
            digits = value
            if len(digits) > 9:
                digits = digits[-9:]
            return digits.zfill(9)

        if re.fullmatch(r"\d{4}[A-Z0-9:_\-]+", value):
            value = value[4:]

        return re.sub(r"[^A-Z0-9:_\-]", "", value)

    def _extract_lin(self, line: str) -> Optional[str]:
        if not line:
            return None

        tokens = re.findall(r"\b[A-Z0-9]{6}\b", line.upper())
        if not tokens:
            return None

        for token in tokens:
            if token.isdigit():
                continue
            if re.fullmatch(r"[A-Z0-9]{6}", token):
                return token
        return None

    def _is_mpo_line(self, line: str) -> bool:
        match = re.match(r"^000\d{3,}\s+([A-Z0-9]{2,8})\b", line.upper())
        return bool(match and re.search(r"[A-Z]", match.group(1)))

    def _extract_serial_candidates(
        self,
        line: str,
        allow_lin_like: bool = False,
        allow_short_numeric: bool = False,
    ) -> List[str]:
        if not line:
            return []

        cleaned = re.sub(r"[^A-Za-z0-9\-/, ]", " ", line).strip()
        if not cleaned:
            return []

        tokens = [token.strip() for token in re.split(r"\s+", cleaned) if token.strip()]

        # Filter out common non-serial words and LIN-like tokens
        stopwords = {
            "COMPUTER",
            "LAPTOP",
            "DELL",
            "HP",
            "LENOVO",
            "SERIAL",
            "NUMBER",
            "NSN",
            "LIN",
            "MPO",
            "DESCRIPTION",
            "POWER",
            "ASSY",
            "ASSEMBLY",
        }

        lin_token = re.compile(r"^(?:[A-Z]\d{4,6}|\d{4,6}[A-Z])$")

        candidates = []
        for token in tokens:
            if not token:
                continue
            if token.upper() in stopwords:
                continue
            if not allow_lin_like and lin_token.match(token.upper()):
                continue
            # allow numeric-only serials such as 941247, but skip MPO numbers like 000000573
            if token.isdigit():
                min_numeric_length = 3 if allow_short_numeric else 4
                if len(token) < min_numeric_length:
                    continue
                if len(token) == 6 and token.startswith("000000"):
                    continue
                if len(token) == 9 and token.startswith("000000"):
                    continue
                candidates.append(token)
                continue

            # ignore short unit-like tokens from description text such as 115V or 1PH.
            if not allow_short_numeric and len(token) <= 4 and re.fullmatch(r"\d+[A-Z]+", token.upper()):
                continue
            if not allow_short_numeric and len(token) <= 4 and re.fullmatch(r"[A-Z]+\d+", token.upper()):
                continue
            # require at least one digit to reduce false positives like 'COMPUTER'
            if not re.search(r"\d", token):
                continue
            # must be composed of allowed chars and reasonable length
            if not re.fullmatch(r"[A-Z0-9\-/,]+", token.upper()):
                continue
            if len(token) < 3:
                continue

            candidates.append(token)
        return candidates

    def _join_serials(self, serials: List[str]) -> Optional[str]:
        if not serials:
            return None
        unique = []
        seen = set()
        for serial in serials:
            serialized = serial.strip()
            if not serialized or serialized in seen:
                continue
            seen.add(serialized)
            unique.append(serialized)
        return "; ".join(unique)

    def _expand_quantities(self, df: pd.DataFrame) -> pd.DataFrame:
        rows: List[Dict[str, object]] = []
        for _, r in df.iterrows():
            qty = int(r.get("quantity") or 1)
            serial_field = r.get("serial_numbers")
            serials: List[str] = []
            if pd.notna(serial_field):
                parts = [p.strip() for p in re.split(r"[;,]", str(serial_field)) if p.strip()]
                serials = parts

            for i in range(max(1, qty)):
                rows.append({
                    "page": r.get("page"),
                    "lin": r.get("lin"),
                    "nsn": r.get("nsn"),
                    "nomenclature": r.get("nomenclature"),
                    "quantity": 1,
                    "serial_number": serials[i] if i < len(serials) else pd.NA,
                })

        if not rows:
            return pd.DataFrame(columns=["page", "lin", "nsn", "nomenclature", "quantity", "serial_number"])
        return pd.DataFrame(rows)


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Parse a PHR PDF into unit-level rows.")
    arg_parser.add_argument("--phr-pdf", required=True, type=Path, help="Path to the PHR PDF.")
    arg_parser.add_argument("--output", required=True, type=Path, help="Output CSV path.")
    args = arg_parser.parse_args()

    parser = PHRTableParser(str(args.phr_pdf))
    df = parser.save_csv(str(args.output))
    print(f"Parsed {len(df)} rows from {args.phr_pdf}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

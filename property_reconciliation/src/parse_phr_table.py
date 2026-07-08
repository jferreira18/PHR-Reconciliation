from __future__ import annotations

import os
import re
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
        # LINs may appear as a leading letter + digits (e.g. D17191) or digits + trailing letter (e.g. 70210N)
        lin_pattern = re.compile(r"\b(?:[A-Z]\d{4,6}|\d{4,6}[A-Z])\b")
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                pending_serials: List[str] = []
                current_record: Optional[Dict[str, object]] = None
                current_mpo_lin: Optional[str] = None
                lookback: List[str] = []

                for line in lines:
                    if self._is_header_line(line):
                        continue

                    item_match = self._match_item_line(line)
                    if item_match:
                        if current_record is not None:
                            current_record["serial_numbers"] = self._join_serials(pending_serials)
                            records.append(current_record)

                        # try to find LIN in recent lookback lines
                        found_lin = None
                        for prev in reversed(lookback[-6:]):
                            m = lin_pattern.search(prev)
                            if m:
                                found_lin = m.group(0)
                                break
                        # if no LIN found, but a current MPO LIN was captured earlier, use it
                        if not found_lin and current_mpo_lin:
                            found_lin = current_mpo_lin

                        current_record = {
                            "page": page_number,
                            "lin": found_lin,
                            "nsn": item_match["nsn"],
                            "nomenclature": item_match["nomenclature"],
                            "quantity": int(item_match["quantity"]),
                            "serial_numbers": None,
                        }
                        pending_serials = []
                        lookback.append(line)
                        continue

                    # capture MPO/LIN lines which may precede NSN rows (e.g. '000000167 63026N POWER...')
                    m_lin_only = lin_pattern.search(line)
                    if m_lin_only and not re.match(r"^\d{8,}", line):
                        current_mpo_lin = m_lin_only.group(0)

                    if current_record is not None:
                        serials = self._extract_serial_candidates(line)
                        if serials:
                            pending_serials.extend(serials)

                    lookback.append(line)

                if current_record is not None:
                    current_record["serial_numbers"] = self._join_serials(pending_serials)
                    records.append(current_record)

        if not records:
            return pd.DataFrame(columns=["page", "lin", "nsn", "nomenclature", "quantity", "serial_numbers"])

        df = pd.DataFrame(records)
        df = df.sort_values(["page", "nsn"]).reset_index(drop=True)
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
        pattern = re.compile(
            r"^(?P<nsn>\d{8,})\s+(?P<nomenclature>.+?)\s+(?P<ui>\S+)\s+(?P<ciic>\S+)\s+(?P<dla>\S+)\s+(?P<uom>\S+)\s+(?P<quantity>\d+)$"
        )
        match = pattern.match(line)
        if not match:
            return None
        return {
            "nsn": match.group("nsn"),
            "nomenclature": match.group("nomenclature").strip(),
            "quantity": match.group("quantity"),
        }

    def _extract_serial_candidates(self, line: str) -> List[str]:
        if not line:
            return []

        cleaned = re.sub(r"[^A-Za-z0-9\- ]", " ", line).strip()
        if not cleaned:
            return []
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
        for token in re.split(r"\s+", cleaned):
            token = token.strip()
            if not token:
                continue
            # exclude pure numbers
            if token.isdigit():
                continue
            # exclude stopwords
            if token.upper() in stopwords:
                continue
            # exclude LIN-like tokens
            if lin_token.match(token.upper()):
                continue
            # require at least one digit to reduce false positives like 'COMPUTER'
            if not re.search(r"\d", token):
                continue
            # must be composed of allowed chars and reasonable length
            if not re.fullmatch(r"[A-Z0-9\-]+", token.upper()):
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
    base_dir = Path(__file__).resolve().parents[1]
    workspace = base_dir.parent
    pdf_path = workspace / "PHR CAO 07JUL.pdf"
    output_path = base_dir / "outputs" / "phr_table.csv"

    parser = PHRTableParser(str(pdf_path))
    df = parser.save_csv(str(output_path))
    print(f"Parsed {len(df)} rows from {pdf_path}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

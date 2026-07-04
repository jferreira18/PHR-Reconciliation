from __future__ import annotations

import os
import re
from typing import List, Dict, Any

import fitz
import pdfplumber
import pandas as pd
import pytesseract
from PIL import Image


ADOBE_FALLBACK_PATTERNS = [
    "to view the full contents of this document",
    "upgrade to the latest version of adobe reader",
    "for further support, go to",
]


DEFAULT_COLUMNS = [
    "source", "page", "raw_text", "serial_number", "description", "lin",
    "nsn", "quantity", "storage_location", "raw_tokens"
]


class PDFPHRExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_rows(self) -> pd.DataFrame:
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        try:
            rows: List[Dict[str, Any]] = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if text.strip():
                        rows.extend(self._parse_page_text(text, page_number, source="text"))
                        continue

                    ocr_text = self._ocr_page(page_number)
                    if ocr_text.strip():
                        rows.extend(self._parse_page_text(ocr_text, page_number, source="ocr"))
                    else:
                        rows.append({
                            "source": "pdf",
                            "page": page_number,
                            "raw_text": "",
                            "serial_number": None,
                            "description": None,
                            "lin": None,
                            "nsn": None,
                            "quantity": None,
                            "storage_location": None,
                            "raw_tokens": "",
                        })

            if self._looks_like_adobe_fallback(rows):
                raise ValueError(
                    "PDF reader issue detected: the source PDF appears to be an Adobe update message rather than the actual PHR document. Please inspect the PDF file and provide the real PHR PDF."
                )

            if not rows:
                raise ValueError(
                    "PDF reader issue detected: no readable content was extracted from the PDF. Please inspect the PDF file and provide a readable PHR document."
                )

            df = pd.DataFrame(rows)
            df = self._normalize_dataframe(df)
            return df
        except Exception as exc:
            raise RuntimeError(
                f"PDF reader issue detected: {exc}. Please inspect the PDF file and verify it contains the actual PHR content."
            ) from exc

    def _parse_page_text(self, text: str, page_number: int, source: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        parsed_rows = []
        for line in lines:
            tokens = [token for token in re.split(r"\s+", line) if token]
            serial_matches = re.findall(r"\b[A-Z0-9][A-Z0-9\-]{2,}\b", line)
            serial = self._choose_serial(serial_matches)
            if serial or line:
                parsed_rows.append({
                    "source": source,
                    "page": page_number,
                    "raw_text": line,
                    "serial_number": serial,
                    "description": self._extract_description(line),
                    "lin": self._extract_lin(line),
                    "nsn": self._extract_nsn(line),
                    "quantity": self._extract_quantity(line),
                    "storage_location": None,
                    "raw_tokens": " | ".join(tokens[:20]),
                })
        return parsed_rows

    def _ocr_page(self, page_number: int) -> str:
        try:
            doc = fitz.open(self.pdf_path)
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            doc.close()
            return text
        except Exception:
            return ""

    def _looks_like_adobe_fallback(self, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return False
        combined = "\n".join(str(row.get("raw_text", "")) for row in rows if row.get("raw_text"))
        normalized = combined.lower()
        return any(pattern in normalized for pattern in ADOBE_FALLBACK_PATTERNS)

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        for col in ["serial_number", "description", "lin", "nsn", "storage_location"]:
            if col in df.columns:
                df[col] = df[col].astype("string").fillna(pd.NA)
        if "quantity" in df.columns:
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        return df

    def _choose_serial(self, serial_matches: List[str]) -> str | None:
        if not serial_matches:
            return None
        candidates = [s for s in serial_matches if len(s) >= 4 and re.search(r"\d", s)]
        if candidates:
            return candidates[0]
        return serial_matches[0]

    def _extract_description(self, line: str) -> str | None:
        cleaned = re.sub(r"\s+", " ", line).strip()
        return cleaned[:200] if cleaned else None

    def _extract_lin(self, line: str) -> str | None:
        match = re.search(r"\b(?:LIN|LIN\s*#?)\s*[:#-]?\s*([A-Z0-9]+)", line, re.I)
        return match.group(1) if match else None

    def _extract_nsn(self, line: str) -> str | None:
        match = re.search(r"\b(?:NSN|NIIN)\s*[:#-]?\s*([0-9A-Z-]+)", line, re.I)
        return match.group(1) if match else None

    def _extract_quantity(self, line: str) -> str | None:
        match = re.search(r"\bQTY\s*[:#-]?\s*(\d+)", line, re.I)
        return match.group(1) if match else None

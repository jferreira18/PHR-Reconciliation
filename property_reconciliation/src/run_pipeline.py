from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from extract_pdf import PDFPHRExtractor
from load_inputs import InputLoader


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    workspace = base_dir.parent

    pdf_path = workspace / "PHR CAO 23JUN26.pdf"
    phr_excel_path = workspace / "PHR CAO 23JUN26.XLSX"
    psd_excel_path = workspace / "PSD PULL_Power BI - DO NOT DELETE.xlsx"

    print("Extracting PDF PHR rows...")
    pdf_extractor = PDFPHRExtractor(str(pdf_path))
    try:
        pdf_df = pdf_extractor.extract_rows()
        print(f"PDF rows extracted: {len(pdf_df)}")
    except Exception as exc:
        print(str(exc))
        print("Skipping PDF-based reconciliation because the source PDF cannot be read as a PHR document.")
        pdf_df = pd.DataFrame(columns=[
            "source", "page", "raw_text", "serial_number", "description", "lin",
            "nsn", "quantity", "storage_location", "raw_tokens"
        ])

    print("Loading Excel PHR input...")
    loader = InputLoader(str(base_dir))
    phr_df = loader.load_phr_excel(str(phr_excel_path))
    print(f"Excel PHR rows loaded: {len(phr_df)}")

    print("Loading PSD workbook...")
    psd_df = loader.load_psd_excel(str(psd_excel_path))
    print(f"PSD rows loaded: {len(psd_df)}")

    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_df.to_csv(output_dir / "pdf_phr_extracted.csv", index=False)
    phr_df.to_csv(output_dir / "excel_phr_normalized.csv", index=False)
    psd_df.to_csv(output_dir / "psd_normalized.csv", index=False)

    print("Saved outputs to", output_dir)


if __name__ == "__main__":
    main()

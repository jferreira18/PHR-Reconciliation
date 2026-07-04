# Property Reconciliation ETL Starter

This folder contains the initial ETL scaffold for the Army PHR-to-PSD reconciliation workflow.

## Current status
- The workbook-based inputs are loaded and normalized into CSV outputs.
- The PDF reader is implemented and produces a raw extraction table for inspection.
- The current PDF file appears to be a viewer prompt rather than a text-bearing hand-receipt document, so the PDF extractor currently captures the fallback message and raw tokens.

## Main modules
- extract_pdf.py: PDF extraction entry point.
- load_inputs.py: workbook loading and column mapping.
- run_pipeline.py: end-to-end starter runner.

## Next steps
1. Replace the current PDF with a text-bearing or OCR-friendly version when available.
2. Add a table extraction step that maps PDF rows to the Excel PHR schema.
3. Preserve serial numbers as a first-class field and join them against the Excel PHR data.

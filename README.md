# Army PHR-to-PSD Reconciliation Project

## Purpose
This project is intended to build a repeatable, auditable workflow for reconciling Army Primary Hand Receipt (PHR) records against Property Support Document (PSD) data. The goal is to determine whether each item on a commander's PHR has an associated PSD and to produce clear outputs for review, reporting, and historical tracking.

## Project Intent
The system is designed to support a repeatable ETL-style process that:
- ingests recurring PHR and PSD input files,
- normalizes the data into a consistent structure,
- reconciles PHR items against PSD coverage,
- identifies exceptions or discrepancies for command review,
- and produces structured outputs suitable for Excel reporting and Power BI use.

The long-term objective is to create a modular reconciliation pipeline that can be reused across future runs without requiring manual code changes whenever the input files are updated.

## Core Business Question
For every item on the Primary Hand Receipt, is there a corresponding PSD record that supports that property accountability requirement?

## Expected Inputs
The initial workflow is built around the following recurring input sources:
- an updated PHR PDF file,
- an updated Excel-based PHR export,
- and an updated PSD workbook export.

The project is intended to use the Excel-based PHR data as the primary structured source where available, while the PDF remains a source for any document-based property details that may be needed for traceability.

## Expected Outputs
The workflow is intended to produce:
- normalized PHR and PSD datasets,
- reconciliation-ready tables,
- Excel-based reporting outputs,
- and Power BI-friendly data structures for dashboarding and trend analysis.

## Design Principles
This project is being built with the following principles in mind:
- repeatability across runs,
- transparency in reconciliation logic,
- auditability of decisions and outputs,
- modularity so future input formats can be supported with mapping changes rather than major code rewrites,
- and clear separation between extraction, normalization, reconciliation, and reporting steps.

## Current Status
This repository currently contains the initial ETL scaffolding and the beginning of a PDF extraction workflow. The project is still in an early implementation stage and will be expanded over time as the reconciliation logic and reporting outputs are completed.

## Future Use
This README should be updated as the implementation evolves. Future versions should document:
- the actual processing steps implemented,
- the schema of the normalized outputs,
- any assumptions made about input files,
- configuration choices,
- and how to run the workflow on new data.

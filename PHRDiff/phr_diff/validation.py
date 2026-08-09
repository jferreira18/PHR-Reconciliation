from __future__ import annotations

from collections import Counter

from .models import HandReceipt, Reconciliation


def classify_validation_warning(warning: str) -> dict[str, str]:
    lowered = warning.lower()
    if "parsed" in lowered and "unique serials" in lowered and "oh qty" in lowered:
        tag = "SERIAL COUNT"
        explanation = "The receipt lists a serialized item, but the number of parsed serials does not match OH Qty."
    elif "lot quantity sum" in lowered:
        tag = "LOT QTY"
        explanation = "Lot quantities were found, but their total does not match OH Qty."
    elif "duplicate stock-number" in lowered:
        tag = "DUPLICATE STOCK"
        explanation = "The same stock-number record appears more than once."
    elif "duplicate serial" in lowered:
        tag = "DUPLICATE SERIAL"
        explanation = "The same serial identifier appears more than once for one item."
    elif "coordinate lookup failure" in lowered:
        tag = "COORDINATE"
        explanation = "A parsed value could not be tied back to a PDF location for highlighting."
    elif "visual bounding box" in lowered:
        tag = "VISUAL BOX"
        explanation = "A changed value was detected, but its visual highlight box is missing."
    elif "page has no extractable text" in lowered or "suspicious property row" in lowered:
        tag = "PARSER"
        explanation = "The parser found text extraction or row parsing evidence that needs review."
    else:
        tag = "VALIDATION"
        explanation = "The reconciliation completed, but this item needs human review."

    return {
        "tag": tag,
        "message": warning,
        "explanation": explanation,
    }


def tagged_validation_warnings(warnings: list[str]) -> list[dict[str, str]]:
    return [classify_validation_warning(warning) for warning in warnings]


def validate_receipt(receipt: HandReceipt) -> list[str]:
    warnings = [
        f"{warning.filename}: page {warning.page}: {warning.reason}: {warning.raw_text}".rstrip()
        for warning in receipt.warnings
    ]

    stock_counts = receipt.stock_counts()
    for stock_number, count in sorted(stock_counts.items()):
        if count > 1:
            warnings.append(f"{receipt.source_file}: duplicate stock-number record {stock_number} appears {count} times.")

    for item in receipt.items:
        serial_ids = [entry.identifier for entry in item.serial_entries]
        for identifier, count in sorted(Counter(serial_ids).items()):
            if count > 1:
                warnings.append(f"{receipt.source_file}: {item.stock_number}: duplicate serial identifier {identifier}.")

        qty_entries = [entry for entry in item.serial_entries if entry.associated_qty is not None]
        if qty_entries:
            total = sum(entry.associated_qty or 0 for entry in qty_entries)
            if total != item.qty:
                warnings.append(
                    f"{receipt.source_file}: {item.stock_number}: lot quantity sum {total} conflicts with OH Qty {item.qty}."
                )
        elif item.serial_entries and len(set(serial_ids)) != item.qty:
            warnings.append(
                f"{receipt.source_file}: {item.stock_number}: parsed {len(set(serial_ids))} unique serials but OH Qty is {item.qty}."
            )

        if item.row_bbox is None or item.qty_bbox is None:
            warnings.append(f"{receipt.source_file}: {item.stock_number}: coordinate lookup failure for property row or quantity.")
        for entry in item.serial_entries:
            if entry.bbox is None:
                warnings.append(f"{receipt.source_file}: {item.stock_number}: coordinate lookup failure for serial {entry.identifier}.")

    return warnings


def validate_reconciliation(reconciliation: Reconciliation) -> list[str]:
    warnings: list[str] = []
    for change in reconciliation.changes:
        old_needs_box = change.old_value is not None and change.old_bbox is None
        new_needs_box = change.new_value is not None and change.new_bbox is None
        if old_needs_box or new_needs_box:
            warnings.append(
                f"{change.stock_number}: changed {change.field} value lacks a visual bounding box ({change.change_type})."
            )
    return warnings


def attach_validation_warnings(reconciliation: Reconciliation, old: HandReceipt, new: HandReceipt) -> None:
    reconciliation.warnings.extend(validate_receipt(old))
    reconciliation.warnings.extend(validate_receipt(new))
    reconciliation.warnings.extend(validate_reconciliation(reconciliation))
    reconciliation.warnings = sorted(set(reconciliation.warnings))

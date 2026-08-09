from __future__ import annotations

from .locator import item_context_bbox
from .models import FieldChange, HandReceipt, InventoryItem, Reconciliation, SerialEntry


def item_map(receipt: HandReceipt) -> dict[str, InventoryItem]:
    result: dict[str, InventoryItem] = {}
    for item in receipt.items:
        result.setdefault(item.stock_number, item)
    return result


def serial_map(item: InventoryItem) -> dict[str, SerialEntry]:
    result: dict[str, SerialEntry] = {}
    for entry in item.serial_entries:
        result.setdefault(entry.identifier, entry)
    return result


def add_change(result: Reconciliation, change: FieldChange) -> None:
    if change.change_type == "item_added":
        result.added_items.append(change)
    elif change.change_type == "item_removed":
        result.removed_items.append(change)
    elif change.change_type.startswith("serial_swap"):
        result.serial_swaps.append(change)
    elif change.change_type in {"metadata_changed"}:
        result.metadata_changes.append(change)
    else:
        result.modified_items.append(change)


def compare_receipts(old: HandReceipt, new: HandReceipt, include_metadata_changes: bool = False) -> Reconciliation:
    result = Reconciliation(baseline_records=len(old.items), current_records=len(new.items))
    old_items = item_map(old)
    new_items = item_map(new)

    for stock_number in sorted(set(new_items) - set(old_items)):
        item = new_items[stock_number]
        add_change(
            result,
            FieldChange(
                stock_number=item.stock_number,
                description=item.description,
                change_type="item_added",
                field="item",
                old_value=None,
                new_value=item.raw_line,
                new_page=item.page,
                new_bbox=item.row_bbox,
                new_context_bbox=item_context_bbox(item),
            ),
        )

    for stock_number in sorted(set(old_items) - set(new_items)):
        item = old_items[stock_number]
        add_change(
            result,
            FieldChange(
                stock_number=item.stock_number,
                description=item.description,
                change_type="item_removed",
                field="item",
                old_value=item.raw_line,
                new_value=None,
                old_page=item.page,
                old_bbox=item.row_bbox,
                old_context_bbox=item_context_bbox(item),
            ),
        )

    for stock_number in sorted(set(old_items) & set(new_items)):
        old_item = old_items[stock_number]
        new_item = new_items[stock_number]
        old_context = item_context_bbox(old_item)
        new_context = item_context_bbox(new_item)

        if old_item.qty != new_item.qty:
            add_change(
                result,
                FieldChange(
                    stock_number=stock_number,
                    description=new_item.description,
                    change_type="quantity_changed",
                    field="qty",
                    old_value=str(old_item.qty),
                    new_value=str(new_item.qty),
                    old_page=old_item.page,
                    new_page=new_item.page,
                    old_bbox=old_item.qty_bbox,
                    new_bbox=new_item.qty_bbox,
                    old_context_bbox=old_context,
                    new_context_bbox=new_context,
                ),
            )

        old_serials = serial_map(old_item)
        new_serials = serial_map(new_item)
        removed = sorted(set(old_serials) - set(new_serials))
        added = sorted(set(new_serials) - set(old_serials))
        is_swap = old_item.qty == new_item.qty and bool(removed) and bool(added)

        for identifier in removed:
            entry = old_serials[identifier]
            add_change(
                result,
                FieldChange(
                    stock_number=stock_number,
                    description=new_item.description,
                    change_type="serial_swap_removed" if is_swap else "serial_removed",
                    field="serial",
                    old_value=identifier,
                    new_value=None,
                    old_page=entry.page,
                    new_page=new_item.page,
                    old_bbox=entry.bbox,
                    old_context_bbox=old_context,
                    new_context_bbox=new_context,
                ),
            )

        for identifier in added:
            entry = new_serials[identifier]
            add_change(
                result,
                FieldChange(
                    stock_number=stock_number,
                    description=new_item.description,
                    change_type="serial_swap_added" if is_swap else "serial_added",
                    field="serial",
                    old_value=None,
                    new_value=identifier,
                    old_page=old_item.page,
                    new_page=entry.page,
                    new_bbox=entry.bbox,
                    old_context_bbox=old_context,
                    new_context_bbox=new_context,
                ),
            )

        for field in ("description", "ui", "ciic", "dla", "buom"):
            old_value = str(getattr(old_item, field))
            new_value = str(getattr(new_item, field))
            if old_value != new_value:
                change = FieldChange(
                    stock_number=stock_number,
                    description=new_item.description,
                    change_type="metadata_changed",
                    field=field,
                    old_value=old_value,
                    new_value=new_value,
                    old_page=old_item.page,
                    new_page=new_item.page,
                    old_bbox=old_item.row_bbox,
                    new_bbox=new_item.row_bbox,
                    old_context_bbox=old_context,
                    new_context_bbox=new_context,
                )
                if include_metadata_changes:
                    add_change(result, change)

    return result

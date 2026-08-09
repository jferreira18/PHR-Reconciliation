from __future__ import annotations

from .models import BBox, FieldChange, InventoryItem


def item_context_bbox(item: InventoryItem, padding_x: float = 12, padding_y: float = 12) -> BBox | None:
    bbox = item.row_bbox
    if bbox is None:
        return None
    for serial in item.serial_entries:
        if serial.bbox:
            bbox = bbox.union(serial.bbox)
    return bbox.padded(padding_x, padding_y)


def highlight_pair(change: FieldChange) -> tuple[list[BBox], list[BBox]]:
    old_highlights: list[BBox] = []
    new_highlights: list[BBox] = []
    if change.old_bbox:
        old_highlights.append(change.old_bbox)
    if change.new_bbox:
        new_highlights.append(change.new_bbox)
    return old_highlights, new_highlights


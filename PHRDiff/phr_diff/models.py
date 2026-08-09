from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf as fitz


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_rect(cls, rect: fitz.Rect) -> "BBox":
        return cls(rect.x0, rect.y0, rect.x1, rect.y1)

    def padded(self, x: float = 8, y: float = 8) -> "BBox":
        return BBox(self.x0 - x, self.y0 - y, self.x1 + x, self.y1 + y)

    def union(self, other: "BBox | None") -> "BBox":
        if other is None:
            return self
        return BBox(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def clamp(self, width: float, height: float) -> "BBox":
        return BBox(
            max(0, min(self.x0, width)),
            max(0, min(self.y0, height)),
            max(0, min(self.x1, width)),
            max(0, min(self.y1, height)),
        )

    def to_rect(self) -> fitz.Rect:
        return fitz.Rect(self.x0, self.y0, self.x1, self.y1)

    @property
    def width(self) -> float:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0, self.y1 - self.y0)


@dataclass
class ParseWarning:
    filename: str
    page: int
    raw_text: str
    reason: str


@dataclass
class SerialEntry:
    identifier: str
    page: int
    bbox: BBox | None
    associated_qty: int | None = None
    raw_text: str | None = None


@dataclass
class InventoryItem:
    stock_number: str
    description: str
    ui: str
    ciic: str
    dla: str
    buom: str
    qty: int
    page: int
    raw_line: str
    row_bbox: BBox | None
    stock_bbox: BBox | None
    description_bbox: BBox | None
    qty_bbox: BBox | None
    serial_entries: list[SerialEntry] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def serials(self) -> list[SerialEntry]:
        return self.serial_entries


@dataclass
class HandReceipt:
    source_file: str
    date: str | None = None
    time: str | None = None
    fe: str | None = None
    uic: str | None = None
    pages: int = 0
    items: list[InventoryItem] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)

    def first_by_stock(self) -> dict[str, InventoryItem]:
        result: dict[str, InventoryItem] = {}
        for item in self.items:
            result.setdefault(item.stock_number, item)
        return result

    def stock_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.stock_number] = counts.get(item.stock_number, 0) + 1
        return counts


@dataclass
class FieldChange:
    stock_number: str
    description: str
    change_type: str
    field: str
    old_value: str | None
    new_value: str | None
    old_page: int | None = None
    new_page: int | None = None
    old_bbox: BBox | None = None
    new_bbox: BBox | None = None
    old_context_bbox: BBox | None = None
    new_context_bbox: BBox | None = None


@dataclass
class Reconciliation:
    added_items: list[FieldChange] = field(default_factory=list)
    removed_items: list[FieldChange] = field(default_factory=list)
    modified_items: list[FieldChange] = field(default_factory=list)
    serial_swaps: list[FieldChange] = field(default_factory=list)
    metadata_changes: list[FieldChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    baseline_records: int = 0
    current_records: int = 0

    @property
    def changes(self) -> list[FieldChange]:
        all_changes: list[FieldChange] = []
        all_changes.extend(self.added_items)
        all_changes.extend(self.removed_items)
        all_changes.extend(self.modified_items)
        all_changes.extend(self.serial_swaps)
        all_changes.extend(self.metadata_changes)
        return sorted(
            all_changes,
            key=lambda c: (
                c.stock_number,
                c.change_type,
                c.field,
                c.old_value or "",
                c.new_value or "",
            ),
        )


@dataclass
class RenderedImage:
    path: Path
    width: int
    height: int
    crop_bbox: BBox
    highlights: list[dict[str, float | str]]
    page: int | None = None

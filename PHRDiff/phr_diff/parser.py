from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

from .models import BBox, HandReceipt, InventoryItem, ParseWarning, SerialEntry


STOCK_DESC_RE = re.compile(r"^(.+?)([A-Z][a-z].*)$")
LOT_QTY_RE = re.compile(r"^(?P<identifier>.+?)\s+-\s+(?P<qty>\d+)$")
METADATA_RE = re.compile(r"^(Date|Time|FE|UIC):\s*(.*)$")


@dataclass
class Word:
    text: str
    bbox: BBox

    @property
    def x0(self) -> float:
        return self.bbox.x0

    @property
    def x1(self) -> float:
        return self.bbox.x1

    @property
    def cy(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2


@dataclass
class Row:
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in sorted(self.words, key=lambda w: w.x0))

    @property
    def bbox(self) -> BBox:
        return bbox_from_words(self.words) or BBox(0, 0, 0, 0)


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def bbox_from_words(words: list[Word]) -> BBox | None:
    if not words:
        return None
    return BBox(
        min(word.bbox.x0 for word in words),
        min(word.bbox.y0 for word in words),
        max(word.bbox.x1 for word in words),
        max(word.bbox.y1 for word in words),
    )


def transform_words(page: fitz.Page) -> list[Word]:
    transformed: list[Word] = []
    for raw in page.get_text("words"):
        rect = fitz.Rect(raw[:4]) * page.rotation_matrix
        transformed.append(Word(str(raw[4]), BBox.from_rect(rect)))
    return transformed


def group_rows(words: list[Word], tolerance: float = 3.2) -> list[Row]:
    rows: list[tuple[float, list[Word]]] = []
    for word in sorted(words, key=lambda w: (w.cy, w.x0)):
        for index, (cy, row_words) in enumerate(rows):
            if abs(cy - word.cy) <= tolerance:
                row_words.append(word)
                rows[index] = (
                    (cy * (len(row_words) - 1) + word.cy) / len(row_words),
                    row_words,
                )
                break
        else:
            rows.append((word.cy, [word]))
    return [Row(sorted(row_words, key=lambda w: w.x0)) for _, row_words in rows]


def is_property_header(row: Row) -> bool:
    text = row.text
    return "NSN" in text and "Description" in text and "OH" in text and "Qty" in text


def is_serial_header(row: Row) -> bool:
    return "SysNo" in row.text and "SerNo/RegNo/LotNo" in row.text


def is_repeated_metadata(row: Row) -> bool:
    text = row.text
    return (
        text == "Primary Hand Receipt"
        or re.match(r"^Page \d+ of \d+$", text) is not None
        or text in {"MPO", "MPO Description"}
    )


def is_mpo_context(row: Row) -> bool:
    text = row.text
    return (
        text in {"MPO", "MPO MPO", "MPO Description", "Sum of Authorizations"}
        or "MPO" in text
        or "Sum of Authorizations" in text
        or text.startswith("Sum of Authorizations")
    )


def column_words(row: Row, left: float, right: float) -> list[Word]:
    return [word for word in row.words if left <= word.x0 < right]


def split_stock_description(first_word: Word, stock_right: float) -> tuple[str, str]:
    text = first_word.text
    if first_word.x1 <= stock_right + 4:
        return text, ""
    match = STOCK_DESC_RE.match(text)
    if match:
        stock, desc = match.groups()
        return stock, desc
    return text, ""


def parse_property_row(row: Row, page_number: int, filename: str) -> tuple[InventoryItem | None, ParseWarning | None]:
    stock_right = 100.0
    desc_left = 100.0
    ui_left = 485.0
    ciic_left = 535.0
    dla_left = 574.0
    buom_left = 622.0
    qty_left = 675.0
    page_right = 792.0

    first_candidates = [word for word in row.words if word.x0 < stock_right]
    qty_words = column_words(row, qty_left, page_right)
    if not first_candidates or not qty_words:
        return None, ParseWarning(filename, page_number, row.text, "Suspicious property row could not be parsed.")

    first = first_candidates[0]
    stock_number, attached_description = split_stock_description(first, stock_right)
    stock_bbox = first.bbox

    description_words = column_words(row, desc_left, ui_left)
    description_parts = []
    if attached_description:
        description_parts.append(attached_description)
        description_words = [word for word in description_words if word is not first]
    description_parts.extend(word.text for word in description_words)
    description = normalize_ws(" ".join(description_parts))

    ui = normalize_ws(" ".join(word.text for word in column_words(row, ui_left, ciic_left)))
    ciic = normalize_ws(" ".join(word.text for word in column_words(row, ciic_left, dla_left)))
    dla = normalize_ws(" ".join(word.text for word in column_words(row, dla_left, buom_left)))
    buom = normalize_ws(" ".join(word.text for word in column_words(row, buom_left, qty_left)))
    qty_text = normalize_ws(" ".join(word.text for word in qty_words))

    if not (stock_number and ui and ciic and dla and buom and qty_text.isdigit()):
        return None, ParseWarning(filename, page_number, row.text, "Suspicious property row could not be parsed.")

    desc_bbox = bbox_from_words(description_words)
    if desc_bbox is None and attached_description:
        desc_bbox = first.bbox

    return (
        InventoryItem(
            stock_number=stock_number,
            description=description,
            ui=ui,
            ciic=ciic,
            dla=dla,
            buom=buom,
            qty=int(qty_text),
            page=page_number,
            raw_line=row.text,
            row_bbox=row.bbox,
            stock_bbox=stock_bbox,
            description_bbox=desc_bbox,
            qty_bbox=bbox_from_words(qty_words),
            provenance={"parser": "pymupdf-rotated-rows"},
        ),
        None,
    )


def parse_serial_segment(words: list[Word], page_number: int) -> SerialEntry | None:
    if not words:
        return None
    text = normalize_ws(" ".join(word.text for word in sorted(words, key=lambda w: w.x0)))
    if not text or text in {"SysNo", "SerNo/RegNo/LotNo"}:
        return None
    match = LOT_QTY_RE.match(text)
    associated_qty = int(match.group("qty")) if match else None
    identifier = match.group("identifier").strip() if match else text
    return SerialEntry(
        identifier=identifier,
        associated_qty=associated_qty,
        page=page_number,
        bbox=bbox_from_words(words),
        raw_text=text,
    )


def parse_serial_row(row: Row, page_number: int) -> list[SerialEntry]:
    serial_ranges = [(45.0, 250.0), (290.0, 495.0), (535.0, 742.0)]
    entries: list[SerialEntry] = []
    for left, right in serial_ranges:
        entry = parse_serial_segment(column_words(row, left, right), page_number)
        if entry:
            entries.append(entry)
    if entries:
        return entries
    entry = parse_serial_segment(row.words, page_number)
    return [entry] if entry else []


def parse_hand_receipt(pdf_path: str | Path) -> HandReceipt:
    path = Path(pdf_path)
    receipt = HandReceipt(source_file=path.name)

    with fitz.open(path) as doc:
        receipt.pages = doc.page_count
        current_item: InventoryItem | None = None
        collecting_serials = False
        awaiting_property = False

        for page_index, page in enumerate(doc):
            page_number = page_index + 1
            words = transform_words(page)
            if not words:
                receipt.warnings.append(ParseWarning(path.name, page_number, "", "Page has no extractable text."))
                continue

            for row in group_rows(words):
                text = row.text
                if not text:
                    continue

                metadata = METADATA_RE.match(text)
                if metadata:
                    name, value = metadata.groups()
                    value = value.strip()
                    if name == "Date" and receipt.date is None:
                        receipt.date = value
                    elif name == "Time" and receipt.time is None:
                        receipt.time = value
                    elif name == "FE" and receipt.fe is None:
                        receipt.fe = value
                    elif name == "UIC" and receipt.uic is None:
                        receipt.uic = value
                    continue

                if is_mpo_context(row):
                    collecting_serials = False
                    awaiting_property = False
                    continue

                if is_repeated_metadata(row):
                    continue

                if is_property_header(row):
                    collecting_serials = False
                    awaiting_property = True
                    continue

                if is_serial_header(row):
                    awaiting_property = False
                    collecting_serials = current_item is not None
                    continue

                if awaiting_property:
                    item, warning = parse_property_row(row, page_number, path.name)
                    awaiting_property = False
                    if warning:
                        receipt.warnings.append(warning)
                        continue
                    assert item is not None
                    if any(existing.stock_number == item.stock_number for existing in receipt.items):
                        receipt.warnings.append(
                            ParseWarning(path.name, page_number, item.raw_line, f"Duplicate stock-number record: {item.stock_number}")
                        )
                    receipt.items.append(item)
                    current_item = item
                    continue

                if collecting_serials and current_item is not None:
                    if re.match(r"^(To|From) \(", text):
                        collecting_serials = False
                        continue
                    current_item.serial_entries.extend(parse_serial_row(row, page_number))

    return receipt

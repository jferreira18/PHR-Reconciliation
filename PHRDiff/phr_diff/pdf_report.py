from __future__ import annotations

from pathlib import Path
from textwrap import shorten

import pymupdf as fitz

from .models import BBox, FieldChange, HandReceipt, Reconciliation
from .validation import tagged_validation_warnings


PAGE_WIDTH = 792
PAGE_HEIGHT = 612
MARGIN = 32
GUTTER = 18
HEADER_HEIGHT = 78
FOOTER_HEIGHT = 28
PANEL_LABEL_HEIGHT = 18
SIDE_PAGE_ROTATION = 270

COLOR_ADDED = (0.14, 0.53, 0.23)
COLOR_REMOVED = (0.81, 0.19, 0.15)
COLOR_CONTEXT = (0.82, 0.61, 0.13)
COLOR_BORDER = (0.72, 0.76, 0.82)
COLOR_TEXT = (0.09, 0.11, 0.16)
COLOR_MUTED = (0.38, 0.43, 0.50)


def generate_pdf_report(
    old_pdf: Path,
    new_pdf: Path,
    old_receipt: HandReceipt,
    new_receipt: HandReceipt,
    reconciliation: Reconciliation,
    output_dir: Path,
    filename: str = "phr-diff-report.pdf",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with fitz.open(old_pdf) as old_doc, fitz.open(new_pdf) as new_doc:
        report = fitz.open()
        _add_summary_page(report, old_pdf, new_pdf, old_receipt, new_receipt, reconciliation)
        page_pairs = _page_pair_entries(reconciliation, old_doc, new_doc)
        for index, entry in enumerate(page_pairs, start=1):
            _add_page_pair(report, old_doc, new_doc, entry, index, len(page_pairs))
        _add_warning_pages(report, reconciliation)
        report.save(output_path, garbage=4, deflate=True)
        report.close()

    return output_path


def _add_summary_page(
    report: fitz.Document,
    old_pdf: Path,
    new_pdf: Path,
    old_receipt: HandReceipt,
    new_receipt: HandReceipt,
    reconciliation: Reconciliation,
) -> None:
    page = report.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, 46), "PHR Diff Side-by-Side PDF Report", fontsize=20, color=COLOR_TEXT)
    page.insert_text((MARGIN, 72), f"Baseline: {old_pdf.name}", fontsize=10, color=COLOR_MUTED)
    page.insert_text((MARGIN, 88), f"Current: {new_pdf.name}", fontsize=10, color=COLOR_MUTED)
    if old_receipt.date or new_receipt.date:
        page.insert_text(
            (MARGIN, 104),
            f"Receipt dates: {old_receipt.date or 'unknown'} -> {new_receipt.date or 'unknown'}",
            fontsize=10,
            color=COLOR_MUTED,
        )

    stats = _summary(reconciliation)
    labels = [
        ("Baseline records", "baseline_records"),
        ("Current records", "current_records"),
        ("Added", "added"),
        ("Removed", "removed"),
        ("Modified", "modified"),
        ("Serial additions", "serial_additions"),
        ("Serial removals", "serial_removals"),
        ("Serial swaps", "serial_swaps"),
        ("Warnings", "validation_warnings"),
        ("Total changes", "changes"),
    ]
    x = MARGIN
    y = 142
    card_w = 136
    card_h = 48
    for i, (label, key) in enumerate(labels):
        row = i // 5
        col = i % 5
        rect = fitz.Rect(x + col * (card_w + 10), y + row * (card_h + 10), x + col * (card_w + 10) + card_w, y + row * (card_h + 10) + card_h)
        page.draw_rect(rect, color=COLOR_BORDER, fill=(0.96, 0.97, 0.98), width=0.7)
        page.insert_text((rect.x0 + 9, rect.y0 + 18), str(stats[key]), fontsize=15, color=COLOR_TEXT)
        page.insert_text((rect.x0 + 9, rect.y0 + 36), label, fontsize=8.5, color=COLOR_MUTED)

    page.insert_text((MARGIN, 308), "Legend", fontsize=13, color=COLOR_TEXT)
    _legend_row(page, MARGIN, 330, COLOR_REMOVED, "Removed or baseline-only value")
    _legend_row(page, MARGIN, 352, COLOR_ADDED, "Added or current-only value")
    _legend_row(page, MARGIN, 374, COLOR_CONTEXT, "Compared row or serial context")

    page.insert_text(
        (MARGIN, 430),
        "Each following page shows the baseline PDF page on the left and the current PDF page on the right.",
        fontsize=10,
        color=COLOR_TEXT,
    )
    page.insert_text(
        (MARGIN, 448),
        "The PDF uses the same comparison data and highlight coordinates as the HTML report.",
        fontsize=10,
        color=COLOR_MUTED,
    )


def _legend_row(page: fitz.Page, x: float, y: float, color: tuple[float, float, float], text: str) -> None:
    rect = fitz.Rect(x, y - 10, x + 16, y + 4)
    page.draw_rect(rect, color=color, fill=color, fill_opacity=0.28, width=1.0)
    page.insert_text((x + 24, y), text, fontsize=9.5, color=COLOR_TEXT)


def _summary(reconciliation: Reconciliation) -> dict[str, int]:
    changes = reconciliation.changes
    return {
        "baseline_records": reconciliation.baseline_records,
        "current_records": reconciliation.current_records,
        "added": len(reconciliation.added_items),
        "removed": len(reconciliation.removed_items),
        "modified": len(reconciliation.modified_items),
        "serial_additions": sum(1 for c in changes if c.change_type in {"serial_added", "serial_swap_added"}),
        "serial_removals": sum(1 for c in changes if c.change_type in {"serial_removed", "serial_swap_removed"}),
        "serial_swaps": len({c.stock_number for c in reconciliation.serial_swaps}),
        "metadata_changes": len(reconciliation.metadata_changes),
        "validation_warnings": len(reconciliation.warnings),
        "changes": len(changes),
    }


def _page_pair_entries(
    reconciliation: Reconciliation,
    old_doc: fitz.Document,
    new_doc: fitz.Document,
) -> list[dict[str, object]]:
    entries: dict[tuple[int | None, int | None], dict[str, object]] = {}
    for change in reconciliation.changes:
        old_page = change.old_page
        new_page = change.new_page
        if old_page is None and new_page is not None and new_page <= old_doc.page_count:
            old_page = new_page
        if new_page is None and old_page is not None and old_page <= new_doc.page_count:
            new_page = old_page

        key = (old_page, new_page)
        entry = entries.setdefault(
            key,
            {
                "old_page": old_page,
                "new_page": new_page,
                "changes": [],
                "old_contexts": [],
                "new_contexts": [],
                "old_highlights": [],
                "new_highlights": [],
            },
        )
        entry["changes"].append(change)  # type: ignore[index, union-attr]
        if change.old_page == old_page:
            if change.old_context_bbox:
                entry["old_contexts"].append(change.old_context_bbox)  # type: ignore[index, union-attr]
            if change.old_bbox:
                entry["old_highlights"].append(change.old_bbox)  # type: ignore[index, union-attr]
        if change.new_page == new_page:
            if change.new_context_bbox:
                entry["new_contexts"].append(change.new_context_bbox)  # type: ignore[index, union-attr]
            if change.new_bbox:
                entry["new_highlights"].append(change.new_bbox)  # type: ignore[index, union-attr]

    return [
        entries[key]
        for key in sorted(entries, key=lambda item: (item[0] or 99999, item[1] or 99999))
    ]


def _add_page_pair(
    report: fitz.Document,
    old_doc: fitz.Document,
    new_doc: fitz.Document,
    entry: dict[str, object],
    index: int,
    total: int,
) -> None:
    page = report.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    old_page = entry["old_page"]
    new_page = entry["new_page"]
    title = f"PDF Page Pair {index} of {total}: baseline page {old_page or '-'} / current page {new_page or '-'}"
    page.insert_text((MARGIN, 38), title, fontsize=15, color=COLOR_TEXT)
    page.insert_text((MARGIN, 58), _page_pair_summary(entry), fontsize=9.5, color=COLOR_MUTED)

    panel_top = MARGIN + HEADER_HEIGHT
    panel_bottom = PAGE_HEIGHT - MARGIN - FOOTER_HEIGHT
    panel_width = (PAGE_WIDTH - (MARGIN * 2) - GUTTER) / 2
    old_panel = fitz.Rect(MARGIN, panel_top, MARGIN + panel_width, panel_bottom)
    new_panel = fitz.Rect(MARGIN + panel_width + GUTTER, panel_top, PAGE_WIDTH - MARGIN, panel_bottom)

    _draw_pdf_side(
        page,
        old_doc,
        old_panel,
        "Baseline",
        old_page if isinstance(old_page, int) else None,
        None,
        entry["old_contexts"],  # type: ignore[arg-type]
        entry["old_highlights"],  # type: ignore[arg-type]
        COLOR_REMOVED,
    )
    _draw_pdf_side(
        page,
        new_doc,
        new_panel,
        "Current",
        new_page if isinstance(new_page, int) else None,
        None,
        entry["new_contexts"],  # type: ignore[arg-type]
        entry["new_highlights"],  # type: ignore[arg-type]
        COLOR_ADDED,
    )

    page.insert_text((MARGIN, PAGE_HEIGHT - 22), "Generated by PHR Diff", fontsize=8, color=COLOR_MUTED)


def _page_pair_summary(entry: dict[str, object]) -> str:
    changes = entry["changes"]
    if not isinstance(changes, list):
        return ""
    labels = [
        f"{change.stock_number} {change.change_type.replace('_', ' ')}"
        for change in changes[:4]
        if isinstance(change, FieldChange)
    ]
    extra = len(changes) - len(labels)
    suffix = f"; +{extra} more" if extra > 0 else ""
    return shorten("; ".join(labels) + suffix, width=145, placeholder="...")


def _full_page_bbox(source_doc: fitz.Document, page_number: int) -> BBox:
    source_page = source_doc[page_number - 1]
    return BBox(0, 0, source_page.rect.width, source_page.rect.height)


def _draw_pdf_side(
    page: fitz.Page,
    source_doc: fitz.Document,
    panel: fitz.Rect,
    label: str,
    page_number: int | None,
    crop_bbox: BBox | None,
    context_bboxes: list[BBox],
    highlights: list[BBox],
    highlight_color: tuple[float, float, float],
) -> None:
    page.insert_text((panel.x0, panel.y0 - 6), label, fontsize=10, color=COLOR_TEXT)
    page.draw_rect(panel, color=COLOR_BORDER, width=0.8)

    if page_number is None:
        _draw_empty_panel(page, panel, f"No {label.lower()} location")
        return

    if crop_bbox is None:
        crop_bbox = _full_page_bbox(source_doc, page_number)

    source_page = source_doc[page_number - 1]
    clip = crop_bbox.clamp(source_page.rect.width, source_page.rect.height).to_rect()
    if clip.is_empty or clip.width <= 0 or clip.height <= 0:
        _draw_empty_panel(page, panel, f"No {label.lower()} crop")
        return

    content_rect = fitz.Rect(panel.x0 + 8, panel.y0 + PANEL_LABEL_HEIGHT, panel.x1 - 8, panel.y1 - 8)
    target = _fit_rect(_rotated_rect(clip, SIDE_PAGE_ROTATION), content_rect)
    page.show_pdf_page(target, source_doc, page_number - 1, clip=clip, rotate=SIDE_PAGE_ROTATION)
    page.draw_rect(target, color=COLOR_BORDER, width=0.6)

    clip_bbox = BBox.from_rect(clip)
    for bbox in context_bboxes:
        mapped = _map_rect(bbox, clip_bbox, target, SIDE_PAGE_ROTATION)
        page.draw_rect(mapped, color=COLOR_CONTEXT, width=1.0)
    for bbox in highlights:
        mapped = _map_rect(bbox, clip_bbox, target, SIDE_PAGE_ROTATION)
        page.draw_rect(mapped, color=highlight_color, fill=highlight_color, fill_opacity=0.22, width=1.2)

    page.insert_text(
        (panel.x0 + 8, panel.y0 + 12),
        f"Page {page_number}",
        fontsize=8.5,
        color=COLOR_MUTED,
    )


def _draw_empty_panel(page: fitz.Page, panel: fitz.Rect, message: str) -> None:
    page.draw_rect(panel, color=COLOR_BORDER, fill=(0.97, 0.97, 0.97), width=0.8)
    text_point = (panel.x0 + 18, panel.y0 + 42)
    page.insert_text(text_point, message, fontsize=10, color=COLOR_MUTED)


def _fit_rect(source: fitz.Rect, target: fitz.Rect) -> fitz.Rect:
    scale = min(target.width / source.width, target.height / source.height)
    width = source.width * scale
    height = source.height * scale
    x0 = target.x0 + (target.width - width) / 2
    y0 = target.y0 + (target.height - height) / 2
    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def _rotated_rect(rect: fitz.Rect, rotation: int) -> fitz.Rect:
    normalized = rotation % 360
    if normalized in (90, 270):
        return fitz.Rect(0, 0, rect.height, rect.width)
    return fitz.Rect(0, 0, rect.width, rect.height)


def _map_rect(bbox: BBox, clip: BBox, target: fitz.Rect, rotation: int = 0) -> fitz.Rect:
    normalized = rotation % 360
    if normalized == 90:
        x_scale = target.width / clip.height
        y_scale = target.height / clip.width
        return fitz.Rect(
            target.x0 + (clip.y1 - bbox.y1) * x_scale,
            target.y0 + (bbox.x0 - clip.x0) * y_scale,
            target.x0 + (clip.y1 - bbox.y0) * x_scale,
            target.y0 + (bbox.x1 - clip.x0) * y_scale,
        )
    if normalized == 180:
        x_scale = target.width / clip.width
        y_scale = target.height / clip.height
        return fitz.Rect(
            target.x0 + (clip.x1 - bbox.x1) * x_scale,
            target.y0 + (clip.y1 - bbox.y1) * y_scale,
            target.x0 + (clip.x1 - bbox.x0) * x_scale,
            target.y0 + (clip.y1 - bbox.y0) * y_scale,
        )
    if normalized == 270:
        x_scale = target.width / clip.height
        y_scale = target.height / clip.width
        return fitz.Rect(
            target.x0 + (bbox.y0 - clip.y0) * x_scale,
            target.y0 + (clip.x1 - bbox.x1) * y_scale,
            target.x0 + (bbox.y1 - clip.y0) * x_scale,
            target.y0 + (clip.x1 - bbox.x0) * y_scale,
        )

    x_scale = target.width / clip.width
    y_scale = target.height / clip.height
    return fitz.Rect(
        target.x0 + (bbox.x0 - clip.x0) * x_scale,
        target.y0 + (bbox.y0 - clip.y0) * y_scale,
        target.x0 + (bbox.x1 - clip.x0) * x_scale,
        target.y0 + (bbox.y1 - clip.y0) * y_scale,
    )


def _add_warning_pages(report: fitz.Document, reconciliation: Reconciliation) -> None:
    warnings = tagged_validation_warnings(reconciliation.warnings)
    if not warnings:
        return

    page = None
    y = PAGE_HEIGHT
    for index, warning in enumerate(warnings, start=1):
        if page is None or y > PAGE_HEIGHT - 54:
            page = report.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            page.insert_text((MARGIN, 42), "Validation Warnings", fontsize=16, color=COLOR_TEXT)
            y = 76

        message = shorten(warning["message"], width=132, placeholder="...")
        explanation = shorten(warning["explanation"], width=118, placeholder="...")
        page.insert_text((MARGIN, y), f"{index}. [{warning['tag']}] {message}", fontsize=9, color=COLOR_TEXT)
        y += 14
        page.insert_text((MARGIN + 16, y), explanation, fontsize=8.2, color=COLOR_MUTED)
        y += 22

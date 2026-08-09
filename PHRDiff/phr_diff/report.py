from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .locator import highlight_pair
from .models import BBox, FieldChange, HandReceipt, Reconciliation, RenderedImage
from .renderer import render_full_page, render_region
from .validation import tagged_validation_warnings
from .web_report import HTML_TEMPLATE


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def summary(reconciliation: Reconciliation) -> dict[str, int]:
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


def image_payload(image: RenderedImage | None, report_dir: Path) -> dict[str, Any] | None:
    if image is None:
        return None
    return {
        "src": image.path.relative_to(report_dir).as_posix(),
        "width": image.width,
        "height": image.height,
        "page": image.page,
        "overlays": image.highlights,
    }


def render_change_assets(
    change: FieldChange,
    index: int,
    old_pdf: Path,
    new_pdf: Path,
    output_dir: Path,
    full_pages: bool,
) -> dict[str, Any]:
    crops_dir = output_dir / "assets" / "crops"
    pages_dir = output_dir / "assets" / "pages"
    old_highlights, new_highlights = highlight_pair(change)
    old_img = None
    new_img = None
    old_page = None
    new_page = None

    if change.old_page and change.old_context_bbox:
        old_img = render_region(
            old_pdf,
            change.old_page,
            change.old_context_bbox,
            crops_dir / f"{index:04d}_old.png",
            old_highlights=old_highlights,
            context_bboxes=[change.old_context_bbox],
        )
        if full_pages:
            old_page = render_full_page(
                old_pdf,
                change.old_page,
                pages_dir / f"{index:04d}_old_page.png",
                old_highlights=old_highlights,
                context_bboxes=[change.old_context_bbox],
            )

    if change.new_page and change.new_context_bbox:
        new_img = render_region(
            new_pdf,
            change.new_page,
            change.new_context_bbox,
            crops_dir / f"{index:04d}_new.png",
            new_highlights=new_highlights,
            context_bboxes=[change.new_context_bbox],
        )
        if full_pages:
            new_page = render_full_page(
                new_pdf,
                change.new_page,
                pages_dir / f"{index:04d}_new_page.png",
                new_highlights=new_highlights,
                context_bboxes=[change.new_context_bbox],
            )

    return {
        "old_crop": image_payload(old_img, output_dir),
        "new_crop": image_payload(new_img, output_dir),
        "old_full_page": image_payload(old_page, output_dir),
        "new_full_page": image_payload(new_page, output_dir),
    }


def generate_report(
    old_pdf: Path,
    new_pdf: Path,
    old_receipt: HandReceipt,
    new_receipt: HandReceipt,
    reconciliation: Reconciliation,
    output_dir: Path,
    full_pages: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    changes = reconciliation.changes
    change_payload = []
    for index, change in enumerate(changes, start=1):
        payload = to_jsonable(change)
        payload["index"] = index
        payload.update(render_change_assets(change, index, old_pdf, new_pdf, output_dir, full_pages))
        change_payload.append(payload)

    data = {
        "old": {"name": old_pdf.name, "source_file": old_receipt.source_file, "date": old_receipt.date},
        "new": {"name": new_pdf.name, "source_file": new_receipt.source_file, "date": new_receipt.date},
        "summary": summary(reconciliation),
        "changes": change_payload,
        "warnings": reconciliation.warnings,
        "warning_details": tagged_validation_warnings(reconciliation.warnings),
    }

    (output_dir / "reconciliation.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    html = HTML_TEMPLATE.replace("__PHR_DATA__", json.dumps(data))
    index = output_dir / "index.html"
    index.write_text(html, encoding="utf-8")
    return index

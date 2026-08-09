from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from .models import BBox, RenderedImage


def _overlay_dict(bbox: BBox, clip: BBox, zoom: float, kind: str) -> dict[str, float | str]:
    return {
        "kind": kind,
        "left": (bbox.x0 - clip.x0) * zoom,
        "top": (bbox.y0 - clip.y0) * zoom,
        "width": bbox.width * zoom,
        "height": bbox.height * zoom,
    }


def render_region(
    pdf_path: Path,
    page_number: int,
    crop_bbox: BBox,
    output_path: Path,
    old_highlights: list[BBox] | None = None,
    new_highlights: list[BBox] | None = None,
    context_bboxes: list[BBox] | None = None,
    zoom: float = 2.0,
) -> RenderedImage:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    old_highlights = old_highlights or []
    new_highlights = new_highlights or []
    context_bboxes = context_bboxes or []

    with fitz.open(pdf_path) as doc:
        page = doc[page_number - 1]
        clip = crop_bbox.clamp(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip.to_rect(), alpha=False)
        pix.save(output_path)

    overlays: list[dict[str, float | str]] = []
    overlays.extend(_overlay_dict(bbox, clip, zoom, "context") for bbox in context_bboxes)
    overlays.extend(_overlay_dict(bbox, clip, zoom, "removed") for bbox in old_highlights)
    overlays.extend(_overlay_dict(bbox, clip, zoom, "added") for bbox in new_highlights)
    return RenderedImage(output_path, pix.width, pix.height, clip, overlays, page_number)


def render_full_page(
    pdf_path: Path,
    page_number: int,
    output_path: Path,
    old_highlights: list[BBox] | None = None,
    new_highlights: list[BBox] | None = None,
    context_bboxes: list[BBox] | None = None,
    zoom: float = 1.35,
) -> RenderedImage:
    with fitz.open(pdf_path) as doc:
        page = doc[page_number - 1]
        full = BBox(0, 0, page.rect.width, page.rect.height)
    return render_region(
        pdf_path,
        page_number,
        full,
        output_path,
        old_highlights=old_highlights,
        new_highlights=new_highlights,
        context_bboxes=context_bboxes,
        zoom=zoom,
    )

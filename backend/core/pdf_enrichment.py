"""Enrich PDF extraction with tables, figures, captions, and quality signals."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import fitz  # PyMuPDF

from config import get_settings

logger = logging.getLogger(__name__)

_CAPTION_RE = {
    "figure": re.compile(r"^(Figure|Fig\.?)\s+\d+", re.I),
    "table": re.compile(r"^(Table|Tbl\.?)\s+\d+", re.I),
}


@dataclass
class EnrichmentResult:
    page_texts: List[dict]
    tables: List[dict]
    figures: List[dict]
    quality: dict
    full_text: str


def _rects_overlap(a: list[float], b: list[float], pad: float = 8.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + pad < bx0
        or bx1 + pad < ax0
        or ay1 + pad < by0
        or by1 + pad < ay0
    )


def _rect_area(r: list[float]) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _intersection_area(a: list[float], b: list[float]) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def suppress_tables_inside_figures(
    tables: list[dict],
    figures: list[dict],
    *,
    overlap_ratio: float = 0.55,
) -> list[dict]:
    """Drop tables whose bbox mostly sits inside a figure (diagram grids)."""
    if not tables or not figures:
        return tables
    kept: list[dict] = []
    for table in tables:
        tb = table.get("bbox")
        if not tb or len(tb) < 4:
            kept.append(table)
            continue
        t_area = _rect_area(tb)
        if t_area <= 0:
            kept.append(table)
            continue
        page = table.get("page")
        inside = False
        for fig in figures:
            if fig.get("page") != page:
                continue
            fb = fig.get("bbox")
            if not fb or len(fb) < 4:
                continue
            if _intersection_area(tb, fb) / t_area >= overlap_ratio:
                inside = True
                break
        if not inside:
            kept.append(table)
    return kept


def _table_confidence(table, markdown: str) -> float:
    try:
        extracted = table.extract() or []
    except Exception:
        extracted = []
    rows = len(extracted)
    cols = len(extracted[0]) if rows and extracted[0] else 0
    score = 0.0
    if rows >= 2 and cols >= 2:
        score += 0.4
    if "|" in markdown and markdown.count("\n") >= 2:
        score += 0.3
    if rows * cols >= 6:
        score += 0.2
    if len(markdown) > 50:
        score += 0.1
    return min(score, 1.0)


def _find_nearby_caption(
    blocks: list[dict],
    bbox: list[float],
    kind: str,
    max_dist: float = 80.0,
) -> Optional[str]:
    """Find a caption line near a region bbox (above or below)."""
    pattern = _CAPTION_RE[kind]
    x0, y0, x1, y1 = bbox
    best: tuple[float, str] | None = None

    for block in blocks:
        text = (block.get("text") or "").strip()
        if not text or not pattern.search(text):
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        # Prefer captions below the region, then above
        if by0 >= y1 - 5:
            dist = by0 - y1
        elif by1 <= y0 + 5:
            dist = y0 - by1
        else:
            # overlapping vertically — still consider if horizontally aligned
            dist = abs((by0 + by1) / 2 - (y0 + y1) / 2)
        if dist > max_dist:
            continue
        # Rough horizontal overlap check
        if bx1 < x0 - 40 or bx0 > x1 + 40:
            continue
        if best is None or dist < best[0]:
            # Keep caption reasonably short
            line = text.split("\n")[0].strip()
            if len(line) > 220:
                line = line[:217] + "..."
            best = (dist, line)
    return best[1] if best else None


def _text_blocks_with_bbox(page: fitz.Page) -> list[dict]:
    blocks: list[dict] = []
    try:
        data = page.get_text("dict")
    except Exception:
        return blocks
    for block in data.get("blocks") or []:
        if block.get("type") != 0:
            continue
        lines = []
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            line_text = "".join(s.get("text", "") for s in spans).strip()
            if line_text:
                lines.append(line_text)
        text = "\n".join(lines).strip()
        if not text:
            continue
        bbox = list(block.get("bbox") or [0, 0, 0, 0])
        blocks.append({"text": text, "bbox": bbox})
    return blocks


def _extract_tables(page: fitz.Page, page_num: int, blocks: list[dict]) -> list[dict]:
    tables: list[dict] = []
    try:
        finder = page.find_tables()
    except Exception as e:
        logger.warning("find_tables failed on page %s: %s", page_num, e)
        return tables

    table_list = getattr(finder, "tables", None) or list(finder)
    for i, table in enumerate(table_list):
        try:
            bbox = list(table.bbox)
            try:
                markdown = table.to_markdown() or ""
            except Exception:
                # Fallback: build crude markdown from extract()
                rows = table.extract() or []
                markdown = "\n".join(
                    "| " + " | ".join(str(c or "") for c in row) + " |"
                    for row in rows
                )
            caption = _find_nearby_caption(blocks, bbox, "table")
            tables.append(
                {
                    "id": f"t_p{page_num}_i{i}",
                    "page": page_num,
                    "bbox": [float(x) for x in bbox],
                    "markdown": markdown,
                    "caption": caption,
                    "confidence": _table_confidence(table, markdown),
                    "rows": table.extract() if hasattr(table, "extract") else None,
                }
            )
        except Exception as e:
            logger.warning("Skipping table %s on page %s: %s", i, page_num, e)
    return tables


def _extract_figures(
    page: fitz.Page, page_num: int, blocks: list[dict]
) -> list[dict]:
    figures: list[dict] = []
    seen: list[list[float]] = []

    # Pass 1: raster images
    try:
        for img_index, img in enumerate(page.get_images(full=True) or []):
            xref = img[0]
            try:
                rects = page.get_image_rects(xref) or []
            except Exception:
                rects = []
            for ri, rect in enumerate(rects):
                bbox = [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]
                # Skip tiny icons
                if (bbox[2] - bbox[0]) < 40 or (bbox[3] - bbox[1]) < 40:
                    continue
                if any(_rects_overlap(bbox, s) for s in seen):
                    continue
                seen.append(bbox)
                caption = _find_nearby_caption(blocks, bbox, "figure")
                figures.append(
                    {
                        "id": f"f_p{page_num}_i{img_index}_{ri}",
                        "page": page_num,
                        "bbox": bbox,
                        "caption": caption,
                        "image_xref": xref,
                        "render_mode": "image",
                    }
                )
    except Exception as e:
        logger.warning("Image extraction failed on page %s: %s", page_num, e)

    # Pass 2: caption-anchored vector figures without image xref
    for bi, block in enumerate(blocks):
        text = (block.get("text") or "").strip()
        if not _CAPTION_RE["figure"].search(text):
            continue
        cap_bbox = block["bbox"]
        # Guess figure region above the caption
        page_rect = page.rect
        guessed = [
            float(cap_bbox[0]),
            float(max(page_rect.y0 + 20, cap_bbox[1] - 280)),
            float(cap_bbox[2]),
            float(cap_bbox[1] - 4),
        ]
        if guessed[3] - guessed[1] < 40:
            continue
        if any(_rects_overlap(guessed, s, pad=20) for s in seen):
            continue
        seen.append(guessed)
        line = text.split("\n")[0].strip()
        figures.append(
            {
                "id": f"f_p{page_num}_c{bi}",
                "page": page_num,
                "bbox": guessed,
                "caption": line[:220],
                "image_xref": None,
                "render_mode": "clip",
            }
        )

    return figures


def enrich_pdf(pdf_bytes: bytes) -> EnrichmentResult:
    """Extract page texts, tables, figures, and quality from a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts: list[dict] = []
    tables: list[dict] = []
    figures: list[dict] = []
    full_parts: list[str] = []
    total_chars = 0

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text() or ""
            cleaned = re.sub(r"\n{3,}", "\n\n", text)
            cleaned = re.sub(r" {2,}", " ", cleaned).strip()
            page_idx = page_num + 1
            page_texts.append({"page": page_idx, "text": cleaned})
            full_parts.append(f"\n\n--- Page {page_idx} ---\n\n{cleaned}")
            total_chars += len(cleaned)

            blocks = _text_blocks_with_bbox(page)
            tables.extend(_extract_tables(page, page_idx, blocks))
            figures.extend(_extract_figures(page, page_idx, blocks))
    finally:
        doc.close()

    tables = suppress_tables_inside_figures(tables, figures)

    num_pages = max(len(page_texts), 1)
    avg_chars = total_chars / num_pages
    quality = {
        "scanned_risk": avg_chars < 100,
        "avg_chars_per_page": round(avg_chars, 1),
        "table_count": len(tables),
        "figure_count": len(figures),
        "enrichment_status": "ready",
        "index_status": "pending",
    }

    return EnrichmentResult(
        page_texts=page_texts,
        tables=tables,
        figures=figures,
        quality=quality,
        full_text="\n".join(full_parts).strip(),
    )


def crop_figure_png(pdf_bytes: bytes, figure: dict) -> bytes:
    """Render a figure region to PNG bytes (2x scale by default)."""
    settings = get_settings()
    scale = settings.figure_render_scale
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc.load_page(int(figure["page"]) - 1)
        bbox = figure["bbox"]
        clip = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        # Expand slightly so labels aren't clipped
        clip = clip + (-4, -4, 4, 4)
        clip = clip & page.rect
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()

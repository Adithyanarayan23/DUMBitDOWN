"""Vision analysis for PDF figure regions."""
from __future__ import annotations

import logging
from typing import Iterator

from config import get_settings
from core.document_store import DocumentStore
from core.llm import safe_generate_text_stream, safe_generate_vision_stream
from core.pdf_enrichment import crop_figure_png
from core.selection_analyzer import FIGURE_CAPTION_ONLY

logger = logging.getLogger(__name__)

FIGURE_EXPLAIN = """You are explaining a figure from a research paper to a college student.

CAPTION: {caption}

Describe what this figure shows and the main takeaway in 1-2 short paragraphs (about 60-100 words).
If labels are hard to read, say what is uncertain. No markdown formatting.
"""

FIGURE_SUMMARIZE = """Summarize this research figure for a college student in 3-5 short bullet points.

CAPTION: {caption}

Focus on the main finding. No markdown bold/italic. Do not invent data you cannot see.
"""


def analyze_figure_stream(
    store: DocumentStore,
    document_id: str,
    *,
    figure_id: str,
    action: str = "explain",
) -> Iterator[tuple[str, bool]]:
    """
    Yield (token, used_vision) for figure analysis.
    Falls back to caption-only text when vision is unavailable.
    """
    doc = store.get(document_id)
    if not doc:
        raise ValueError("Document not found or expired")

    figure = store.get_figure(document_id, figure_id)
    if not figure:
        raise ValueError("Figure not found")

    caption = figure.get("caption") or "No caption provided"
    prompt_tpl = FIGURE_SUMMARIZE if action == "summarize" else FIGURE_EXPLAIN
    prompt = prompt_tpl.format(caption=caption)

    settings = get_settings()
    provider = (settings.llm_provider or "google").strip().lower()

    if provider != "google":
        # Groq / non-vision: caption only
        fallback = FIGURE_CAPTION_ONLY.format(caption=caption)
        for chunk in safe_generate_text_stream(fallback):
            yield chunk, False
        return

    pdf_bytes = store.read_pdf_bytes(document_id)
    if not pdf_bytes:
        fallback = FIGURE_CAPTION_ONLY.format(caption=caption)
        for chunk in safe_generate_text_stream(fallback):
            yield chunk, False
        return

    try:
        image_bytes = crop_figure_png(pdf_bytes, figure)
    except Exception as e:
        logger.warning("Figure crop failed: %s", e)
        fallback = FIGURE_CAPTION_ONLY.format(caption=caption)
        for chunk in safe_generate_text_stream(fallback):
            yield chunk, False
        return

    try:
        for chunk in safe_generate_vision_stream(prompt, image_bytes):
            yield chunk, True
    except Exception as e:
        logger.warning("Vision stream failed, falling back to caption: %s", e)
        fallback = FIGURE_CAPTION_ONLY.format(caption=caption)
        for chunk in safe_generate_text_stream(fallback):
            yield chunk, False

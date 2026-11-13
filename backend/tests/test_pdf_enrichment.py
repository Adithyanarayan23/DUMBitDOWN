"""Unit tests for PDF enrichment and selection stream buffering."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _make_simple_pdf() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Attention Is All You Need")
    page.insert_text((72, 100), "Abstract: We propose a new simple network architecture.")
    page.insert_text((72, 140), "Table 1: BLEU scores on WMT")
    # Draw a simple table-like grid
    page.draw_rect(fitz.Rect(72, 160, 400, 260), color=(0, 0, 0), width=0.5)
    page.insert_text((80, 180), "Model   BLEU")
    page.insert_text((80, 200), "Base    27.3")
    page.insert_text((80, 220), "Big     28.4")
    page.insert_text((72, 300), "Figure 1: Multi-head attention architecture")
    data = doc.tobytes()
    doc.close()
    return data


def test_enrich_pdf_basic():
    fitz = pytest.importorskip("fitz")
    from core.pdf_enrichment import enrich_pdf

    pdf = _make_simple_pdf()
    result = enrich_pdf(pdf)
    assert result.quality["avg_chars_per_page"] > 0
    assert result.quality["scanned_risk"] is False
    assert len(result.page_texts) >= 1
    assert "Attention" in result.full_text or "architecture" in result.full_text.lower()


def test_process_and_enrich_single_pass():
    pytest.importorskip("fitz")
    try:
        from core.pdf_processor import PDFProcessor
    except ModuleNotFoundError as e:
        pytest.skip(f"PDFProcessor deps missing: {e}")

    pdf = _make_simple_pdf()
    processed = PDFProcessor().process_and_enrich(pdf, "test.pdf", document_id="abc")
    assert processed.enrichment is not None
    assert processed.chunks
    assert processed.documents
    assert processed.documents[0].metadata["source"] == "upload:abc"
    assert processed.documents[0].metadata["document_id"] == "abc"


def test_visible_stream_hides_terms_trailer():
    from core.selection_analyzer import TERMS_SPLIT, _visible_stream_text, finalize_response

    partial = "Hello world\n---TERMS_JS"
    # Incomplete trailer must not fully flush
    vis = _visible_stream_text(partial, strip_header=False)
    assert "TERMS_JSON" not in vis or vis.endswith("---") is False

    full = (
        "SIMPLIFIED EXPLANATION:\n"
        "This is plain text.\n\n"
        f"{TERMS_SPLIT}\n"
        '[{"term":"BLEU","definition":"a score"}]'
    )
    vis2 = _visible_stream_text(full, strip_header=True)
    assert "TERMS_JSON" not in vis2
    assert "This is plain text" in vis2

    final = finalize_response(full, action="simplify")
    assert "TERMS_JSON" not in final
    assert "This is plain text" in final


def test_table_confidence_helper():
    pytest.importorskip("fitz")
    from core.pdf_enrichment import _table_confidence

    class FakeTable:
        def extract(self):
            return [["A", "B"], ["1", "2"], ["3", "4"]]

    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    score = _table_confidence(FakeTable(), md)
    assert score >= 0.7


def test_suppress_tables_inside_figures():
    from core.pdf_enrichment import suppress_tables_inside_figures

    figures = [{"id": "f1", "page": 1, "bbox": [0, 0, 200, 200]}]
    tables = [
        {"id": "t1", "page": 1, "bbox": [10, 10, 100, 100]},
        {"id": "t2", "page": 1, "bbox": [250, 10, 400, 100]},
        {"id": "t3", "page": 2, "bbox": [10, 10, 100, 100]},
    ]
    kept = suppress_tables_inside_figures(tables, figures)
    ids = {t["id"] for t in kept}
    assert "t1" not in ids
    assert "t2" in ids
    assert "t3" in ids

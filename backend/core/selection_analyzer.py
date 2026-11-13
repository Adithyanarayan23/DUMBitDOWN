"""Analyze selected text / tables from an uploaded PDF document."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterator, Optional
from dataclasses import dataclass, field

from core.document_store import DocumentStore, StoredDocument
from core.llm import safe_generate_text_stream
from core.simplification import TERMS_SPLIT, _parse_terms_json

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[str, list[dict]]] = {}
_CACHE_MAX = 128

LIGHT_RAG_MIN_CHARS = 300


@dataclass
class AnalyzeResultBag:
    """Filled by analyze_stream when the generator completes."""
    text: str = ""
    terms: list[dict] = field(default_factory=list)


TEXT_SUMMARIZE = """You are helping a college student understand research text.

SELECTED TEXT (from page {page}):
{text}

NEARBY CONTEXT:
{context}

Summarize the key points in 3-5 short bullet points in plain English.
Do NOT use markdown bold/italic. Do not invent facts not present in the text.
"""

TEXT_SIMPLIFY = """You are an AI assistant that simplifies complex research text for college students.

SELECTED TEXT:
{text}

NEARBY CONTEXT (use only if helpful):
{context}

Rephrase the selected text so a college student can understand it.
Be brief: 1-2 short paragraphs max (about 60-100 words). Do NOT use markdown formatting.
After the explanation, list up to 4 technical terms with short definitions.

Output EXACTLY:
SIMPLIFIED EXPLANATION:
<plain text>

---TERMS_JSON---
[{{"term":"example","definition":"short definition"}}]
"""

TEXT_EXPLAIN = """You are explaining a research passage to a college student.

SELECTED TEXT (page {page}):
{text}

NEARBY CONTEXT:
{context}

Explain what this means in plain English in 1-2 short paragraphs (about 60-100 words).
Clarify jargon briefly. No markdown formatting.
"""

TEXT_ASK = """You are answering a student's question about a research passage.

QUESTION: {question}

PASSAGE (page {page}):
{text}

NEARBY CONTEXT:
{context}

Answer in 2-4 short sentences. Be direct. No markdown formatting.
"""

TEXT_TERMS = """Extract up to 8 technical terms from this research text and define them briefly for a college student.

TEXT:
{text}

Output EXACTLY:
DEFINITIONS:
(short intro optional)

---TERMS_JSON---
[{{"term":"example","definition":"short definition"}}]
"""

TABLE_SUMMARIZE = """You are helping a student understand a table from a research paper.

CAPTION: {caption}

TABLE (markdown):
{markdown}

Summarize the key findings in 3-5 bullet points.
Call out important numbers, comparisons, and trends.
Do not invent data not present in the table. No markdown bold/italic.
"""

TABLE_EXPLAIN = """You are helping a student read a research table.

CAPTION: {caption}

TABLE (markdown):
{markdown}

Explain what each column means and how to read the table.
Then give the main takeaway in 2-3 sentences. No markdown bold/italic.
"""

TABLE_SIMPLIFY = """Turn this research table into a plain-English explanation for a college student.

CAPTION: {caption}

TABLE (markdown):
{markdown}

Write 1-2 short paragraphs (about 60-100 words). Do not invent numbers. No markdown formatting.
"""

FIGURE_CAPTION_ONLY = """You are explaining a figure from a research paper using only its caption (no image available).

CAPTION: {caption}

Explain what this figure is likely showing and the main takeaway in 1-2 short paragraphs.
Be honest about uncertainty since you cannot see the image. No markdown.
"""


def _cache_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _page_neighbors(doc: StoredDocument, page: Optional[int], selected: str) -> str:
    if not page:
        return ""
    page_text = ""
    if doc.page_texts:
        for pt in doc.page_texts:
            if pt.get("page") == page:
                page_text = pt.get("text") or ""
                break
    if not page_text and doc.full_text:
        marker = f"--- Page {page} ---"
        if marker in doc.full_text:
            after = doc.full_text.split(marker, 1)[1]
            next_marker = re.search(r"--- Page \d+ ---", after)
            page_text = after[: next_marker.start()] if next_marker else after

    if not page_text:
        return ""

    idx = page_text.find(selected[:80]) if selected else -1
    if idx >= 0:
        start = max(0, idx - 400)
        end = min(len(page_text), idx + len(selected) + 400)
        return page_text[start:end].strip()
    return page_text[:1200]


def _chunk_overlap_context(doc: StoredDocument, selected: str, top_n: int = 3) -> str:
    """Fallback same-doc context via simple token overlap on stored chunks."""
    chunks = doc.chunks or []
    if not chunks or not selected:
        return ""
    terms = {t.lower() for t in re.findall(r"[A-Za-z]{3,}", selected)}
    if not terms:
        return ""
    scored: list[tuple[float, str]] = []
    for chunk in chunks[:150]:
        words = {t.lower() for t in re.findall(r"[A-Za-z]{3,}", chunk)}
        if not words:
            continue
        overlap = len(terms & words) / max(len(terms), 1)
        if overlap > 0:
            scored.append((overlap, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    parts = [c for _, c in scored[:top_n]]
    return "\n\n".join(parts)


def _same_doc_rag_context(document_id: str, selected: str, doc: StoredDocument) -> str:
    """Light RAG: retrieve FAISS hits for this upload, else chunk overlap."""
    if len(selected) < LIGHT_RAG_MIN_CHARS:
        return ""
    try:
        from core.retrieval import format_context, get_shared_retriever

        source = f"upload:{document_id}"
        own = get_shared_retriever().retrieve_for_source(selected[:800], source, k=3)
        if own:
            return format_context(own)
    except Exception as e:
        logger.debug("Same-doc FAISS filter skipped: %s", e)

    return _chunk_overlap_context(doc, selected)


def build_prompt(
    *,
    content_type: str,
    action: str,
    text: str = "",
    page: Optional[int] = None,
    markdown: str = "",
    caption: str = "",
    context: str = "",
    question: str = "",
) -> str:
    if content_type == "text":
        if action == "summarize":
            return TEXT_SUMMARIZE.format(text=text, page=page or "?", context=context)
        if action == "simplify":
            return TEXT_SIMPLIFY.format(text=text, context=context)
        if action == "explain":
            return TEXT_EXPLAIN.format(text=text, page=page or "?", context=context)
        if action == "define_terms":
            return TEXT_TERMS.format(text=text)
        if action == "ask":
            return TEXT_ASK.format(
                question=question or "What does this mean?",
                text=text,
                page=page or "?",
                context=context,
            )
    if content_type == "table":
        if action == "explain":
            return TABLE_EXPLAIN.format(markdown=markdown, caption=caption or "None")
        if action == "simplify":
            return TABLE_SIMPLIFY.format(markdown=markdown, caption=caption or "None")
        return TABLE_SUMMARIZE.format(markdown=markdown, caption=caption or "None")
    if content_type == "figure":
        return FIGURE_CAPTION_ONLY.format(caption=caption or "No caption")
    raise ValueError(f"Unsupported content_type={content_type} action={action}")


def _visible_stream_text(raw: str, *, strip_header: bool) -> str:
    """
    Return user-visible prose from a partial model response.
    Buffers ---TERMS_JSON--- so it never leaks to the client mid-stream.
    """
    trailer_seen = TERMS_SPLIT in raw
    prose = raw.split(TERMS_SPLIT, 1)[0] if trailer_seen else raw

    header = "SIMPLIFIED EXPLANATION:"
    if strip_header and header in prose:
        prose = prose.split(header, 1)[1].lstrip("\n")

    if trailer_seen:
        return prose.strip() if strip_header else prose.rstrip()

    # Hold back suffix so a partial TERMS marker or header never flashes
    holdback = len(TERMS_SPLIT)
    if strip_header and header not in raw:
        holdback = max(holdback, len(header))
    return prose[: max(0, len(prose) - holdback)]


def finalize_response(raw: str, *, action: str) -> str:
    """Clean final model text for caching / done event."""
    body, _ = split_terms(raw)
    header = "SIMPLIFIED EXPLANATION:"
    if action == "simplify" and header in body:
        body = body.split(header, 1)[1].lstrip("\n")
    if action == "define_terms":
        # Prefer empty body if only JSON was produced; UI shows terms list
        body = re.sub(r"^DEFINITIONS:\s*", "", body, flags=re.I).strip()
    return body.strip()


def analyze_stream(
    store: DocumentStore,
    document_id: str,
    *,
    content_type: str,
    action: str,
    text: Optional[str] = None,
    page: Optional[int] = None,
    table_id: Optional[str] = None,
    question: Optional[str] = None,
    result_bag: Optional[AnalyzeResultBag] = None,
) -> Iterator[str]:
    """
    Yield visible LLM text tokens for a text/table analysis.
    Never streams the TERMS_JSON trailer; strips simplify header.
    Populates result_bag with final text + terms when done.
    """
    doc = store.get(document_id)
    if not doc:
        raise ValueError("Document not found or expired")

    markdown = ""
    caption = ""
    selected = (text or "").strip()
    ask_question = (question or "").strip()

    if content_type == "table":
        table = store.get_table(document_id, table_id or "")
        if not table:
            raise ValueError("Table not found")
        markdown = table.get("markdown") or ""
        caption = table.get("caption") or ""
        page = table.get("page")
        if not markdown:
            raise ValueError("Table has no extractable content")
    elif content_type == "text":
        if not selected or len(selected) < 10:
            raise ValueError("Selected text too short (min 10 characters)")
        if len(selected) > 5000:
            selected = selected[:5000]
        if action == "ask" and not ask_question:
            ask_question = "What does this mean?"
    else:
        raise ValueError("Use vision endpoint for figures")

    context = ""
    if content_type == "text":
        neighbors = _page_neighbors(doc, page, selected)
        if not neighbors and page:
            pt = store.get_page_text(document_id, page)
            if pt:
                neighbors = pt[:1200]
        rag = _same_doc_rag_context(document_id, selected, doc)
        if neighbors and rag:
            context = f"{neighbors}\n\nRELATED PASSAGES FROM THIS PAPER:\n{rag}"
        else:
            context = neighbors or rag

    prompt = build_prompt(
        content_type=content_type,
        action=action,
        text=selected,
        page=page,
        markdown=markdown,
        caption=caption,
        context=context,
        question=ask_question,
    )

    key = _cache_key(
        document_id,
        content_type,
        action,
        table_id or "",
        selected[:500],
        markdown[:500],
        ask_question[:200],
    )
    if key in _CACHE:
        cached_text, cached_terms = _CACHE[key]
        if result_bag is not None:
            result_bag.text = cached_text
            result_bag.terms = cached_terms
        yield cached_text
        return

    strip_header = action == "simplify"
    raw = ""
    emitted = 0
    for chunk in safe_generate_text_stream(prompt):
        raw += chunk
        visible = _visible_stream_text(raw, strip_header=strip_header)
        if len(visible) > emitted:
            yield visible[emitted:]
            emitted = len(visible)

    _, terms = split_terms(raw)
    final_visible = finalize_response(raw, action=action)
    if len(final_visible) > emitted:
        yield final_visible[emitted:]
    elif emitted == 0 and final_visible:
        yield final_visible

    if result_bag is not None:
        result_bag.text = final_visible
        result_bag.terms = terms

    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (final_visible, terms)


def split_terms(full_text: str) -> tuple[str, list[dict]]:
    """Split explanation from optional TERMS_JSON trailer."""
    if not full_text:
        return "", []
    if TERMS_SPLIT not in full_text:
        return full_text.strip(), []
    body, raw = full_text.split(TERMS_SPLIT, 1)
    return body.strip(), _parse_terms_json(raw)

"""RAG retrieval evaluation harness.

Run from backend/:
  pytest tests -q -m "not integration"
  pytest tests -q   # includes Gemini integration if GOOGLE_API_KEY set
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

# Ensure backend package root is on path
BACKEND_DIR = Path(__file__).resolve().parents[1]
import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVAL_PATH = Path(__file__).parent / "eval_queries.json"


def _load_queries():
    with open(EVAL_PATH, encoding="utf-8") as f:
        return json.load(f)


def _has_faiss() -> bool:
    from config import get_settings

    settings = get_settings()
    path = settings.vector_store_path
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return (path / "index.faiss").exists() and (path / "index.pkl").exists()


@pytest.fixture(scope="module")
def app_client():
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    if not _has_faiss():
        pytest.skip("FAISS index missing — run ingest_data.py")

    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client


@pytest.mark.unit
def test_eval_queries_file_shape():
    queries = _load_queries()
    assert len(queries) >= 15
    for q in queries:
        assert "id" in q and "query" in q
        assert len(q["query"]) >= 5


@pytest.mark.unit
def test_health_requires_key_or_skip():
    """Config validation: settings need GOOGLE_API_KEY at import time for app."""
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    from config import get_settings

    s = get_settings()
    assert s.embedding_model
    assert s.normalize_embeddings is False or isinstance(s.normalize_embeddings, bool)


@pytest.mark.integration
def test_health_endpoint(app_client):
    res = app_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "checks" in data
    assert data["checks"].get("vector_store") == "ok"


@pytest.mark.integration
def test_retrieval_returns_docs_with_titles():
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    if not _has_faiss():
        pytest.skip("FAISS index missing")

    from core.retrieval import Retriever

    retriever = Retriever()
    queries = _load_queries()[:10]
    for item in queries:
        docs = retriever.retrieve(item["query"], k=5)
        assert len(docs) > 0, f"No docs for {item['id']}"
        for doc, score in docs:
            title = (doc.metadata or {}).get("title") or ""
            # Title may be Unknown; page content often has Title:
            content = doc.page_content or ""
            has_title = bool(title and title not in ("Untitled", "")) or "Title:" in content
            assert has_title, f"Empty title for {item['id']}"
            assert isinstance(score, (int, float))


@pytest.mark.integration
def test_citations_contribution_sums(app_client):
    queries = _load_queries()
    paste = next(q for q in queries if q["type"] == "paste")
    res = app_client.post(
        "/api/search",
        json={"query": paste["query"], "k": 5},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    sources = (data.get("citations") or {}).get("sources") or []
    assert len(sources) > 0
    total = sum(float(s.get("contribution") or s.get("contribution_percentage") or 0) for s in sources)
    assert 95 <= total <= 105, f"contribution sum {total}"
    for s in sources:
        assert s.get("title")
        urls = s.get("urls") or {}
        assert urls.get("scholar") or s.get("title")


@pytest.mark.integration
def test_keyword_overlap_proxy():
    """Simple groundedness: top chunk shares a content word with the query."""
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    if not _has_faiss():
        pytest.skip("FAISS index missing")

    from core.retrieval import Retriever

    retriever = Retriever()
    stop = {
        "the", "a", "an", "and", "or", "of", "in", "to", "for", "is", "are",
        "with", "on", "as", "by", "at", "from", "that", "this", "such",
    }
    hits = 0
    checked = 0
    for item in _load_queries()[:12]:
        docs = retriever.retrieve(item["query"], k=3)
        if not docs:
            continue
        checked += 1
        top = docs[0][0].page_content.lower()
        tokens = {
            t
            for t in re.findall(r"[a-z0-9-]{4,}", item["query"].lower())
            if t not in stop
        }
        if any(t in top for t in tokens):
            hits += 1
    assert checked > 0
    assert hits / checked >= 0.5, f"keyword overlap {hits}/{checked}"


@pytest.mark.integration
def test_pipeline_meta_present(app_client):
    res = app_client.post(
        "/api/search",
        json={"query": "IL-6 cytokine inflammation CRP", "k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert "pipeline" in data
    assert data["pipeline"].get("model")
    assert "top_scores" in data["pipeline"]

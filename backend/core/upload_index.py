"""Ephemeral in-memory FAISS indexes for uploaded PDFs.

Keeps uploads out of the shared PubMed FAISS corpus on disk.
"""
from __future__ import annotations

import logging
import threading
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from core.embeddings import get_cached_embeddings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_stores: dict[str, FAISS] = {}
_doc_stores: dict[str, List[Document]] = {}


def index_upload_documents(document_id: str, documents: List[Document]) -> int:
    """Build/replace an in-memory index for one upload. Never writes to disk."""
    if not document_id or not documents:
        return 0
    docs = documents[:150]
    with _lock:
        _doc_stores[document_id] = docs
        try:
            embeddings = get_cached_embeddings()
            store = FAISS.from_documents(docs, embeddings)
            _stores[document_id] = store
        except Exception as e:
            logger.info("Using BM25 upload index for %s: %s", document_id, e)
        logger.info(
            "Ephemeral upload index ready for %s (%s chunks)",
            document_id,
            len(docs),
        )
        return len(docs)


def retrieve_upload(
    document_id: str, query: str, k: int = 3
) -> List[Tuple[Document, float]]:
    if not document_id or not query.strip():
        return []
    with _lock:
        store = _stores.get(document_id)
        if store is not None:
            return store.similarity_search_with_score(query, k=k)
        docs = _doc_stores.get(document_id)
        if not docs:
            return []
        from core.seed_corpus import hybrid_bm25_search
        return hybrid_bm25_search(query, docs, k=k)


def drop_upload_index(document_id: str) -> bool:
    with _lock:
        existed = document_id in _stores or document_id in _doc_stores
        _stores.pop(document_id, None)
        _doc_stores.pop(document_id, None)
        return existed


def has_upload_index(document_id: str) -> bool:
    with _lock:
        return document_id in _stores or document_id in _doc_stores

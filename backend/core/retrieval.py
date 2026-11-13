"""Vector store retrieval supporting both FAISS (local) and Qdrant (cloud)."""
import inspect
import threading
from abc import ABC, abstractmethod
from typing import List, Tuple
import logging

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from config import get_settings
from core.embeddings import get_cached_embeddings

logger = logging.getLogger(__name__)

# Serialize FAISS mutate+save (shared PubMed index on disk)
_faiss_write_lock = threading.Lock()


def _is_upload_source(meta: dict | None) -> bool:
    if not meta:
        return False
    source = str(meta.get("source") or "")
    if source.startswith("upload:"):
        return True
    if meta.get("type") == "pdf_upload":
        return True
    return False


def _without_uploads(
    results: List[Tuple[Document, float]],
) -> List[Tuple[Document, float]]:
    """Keep the PubMed corpus clean in paste / general retrieval."""
    return [(d, s) for d, s in results if not _is_upload_source(d.metadata)]


def format_context(documents: List[Tuple[Document, float]]) -> str:
    """Format retrieved documents into a prompt context string."""
    if not documents:
        return "No relevant context found."

    context_parts = [
        "BACKGROUND REFERENCE MATERIAL "
        "(silent background knowledge only; never quote, cite, number, or refer to it):\n"
    ]
    seen_content = set()

    for doc, score in documents:
        content = doc.page_content.strip()
        if content in seen_content:
            continue
        seen_content.add(content)

        title = doc.metadata.get("title")
        if title and title not in ("Unknown Title", "Untitled"):
            context_parts.append(f"\n[{title}]")
        else:
            context_parts.append("")
        context_parts.append(content)

    return "\n".join(context_parts)


class BaseRetriever(ABC):
    """Abstract base class for vector store retrievers."""

    @abstractmethod
    def retrieve(self, query: str, k: int | None = None) -> List[Tuple[Document, float]]:
        """Retrieve similar documents for the given query."""
        pass

    def get_context(self, query: str, k: int | None = None) -> str:
        """Get formatted context string for a query."""
        return format_context(self.retrieve(query, k=k))


class FAISSRetriever(BaseRetriever):
    """Local FAISS-based retriever with automatic seed-corpus fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self.vector_store_path = settings.vector_store_path
        if not self.vector_store_path.is_absolute():
            from pathlib import Path
            self.vector_store_path = Path(__file__).resolve().parents[1] / self.vector_store_path
        self.top_k = settings.top_k
        self._vector_store: FAISS | None = None
        self._fallback_docs: List[Document] = []
        self._load_vector_store()

    def _load_vector_store(self) -> None:
        index_path = self.vector_store_path / "index.faiss"
        docstore_path = self.vector_store_path / "index.pkl"

        if index_path.exists() and docstore_path.exists():
            try:
                logger.info("Loading FAISS vector store from %s", self.vector_store_path)
                embeddings = get_cached_embeddings()
                load_kwargs = {}
                if "allow_dangerous_deserialization" in inspect.signature(FAISS.load_local).parameters:
                    load_kwargs["allow_dangerous_deserialization"] = True
                self._vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    embeddings,
                    **load_kwargs,
                )
                logger.info("FAISS vector store loaded successfully")
                return
            except Exception as e:
                logger.warning("FAISS load failed (%s); falling back to seed corpus", e)

        from core.seed_corpus import get_seed_documents

        self._fallback_docs = get_seed_documents()
        try:
            embeddings = get_cached_embeddings()
            self._vector_store = FAISS.from_documents(self._fallback_docs, embeddings)
            self.vector_store_path.mkdir(parents=True, exist_ok=True)
            self._vector_store.save_local(str(self.vector_store_path))
            logger.info("Built and saved seed FAISS vector store at %s", self.vector_store_path)
        except Exception as e:
            logger.info(
                "Using built-in Hybrid BM25 + N-gram seed retriever (%s papers): %s",
                len(self._fallback_docs),
                e,
            )

    def retrieve(self, query: str, k: int | None = None) -> List[Tuple[Document, float]]:
        k = k or self.top_k
        fetch_k = max(k * 2, k + 4)
        if self._vector_store is not None:
            results = self._vector_store.similarity_search_with_score(query, k=fetch_k)
            cleaned = _without_uploads(results)[:k]
            logger.info(
                "FAISS: Retrieved %s documents (%s after excluding uploads)",
                len(results),
                len(cleaned),
            )
            return cleaned

        from core.seed_corpus import hybrid_bm25_search

        results = hybrid_bm25_search(query, self._fallback_docs, k=fetch_k)
        return _without_uploads(results)[:k]

    def has_source(self, source: str) -> bool:
        """Return True if any indexed doc already uses this source id."""
        if self._vector_store is None:
            return False
        try:
            # Prefer docstore scan (fast, exact) over similarity search
            store = getattr(self._vector_store, "docstore", None)
            docs = getattr(store, "_dict", None) if store else None
            if isinstance(docs, dict):
                for doc in docs.values():
                    meta = getattr(doc, "metadata", None) or {}
                    if meta.get("source") == source:
                        return True
            return False
        except Exception as e:
            logger.warning("has_source check failed: %s", e)
            return False

    def add_documents(self, documents: List[Document], source: str | None = None) -> int:
        """
        Embed and persist new documents into the local FAISS index.
        Skips upload sources (use core.upload_index instead).
        Skips if `source` is already present. Returns number of chunks added.
        """
        if self._vector_store is None:
            raise RuntimeError("Vector store not loaded")
        if not documents:
            return 0

        src = source or (documents[0].metadata or {}).get("source")
        if src and str(src).startswith("upload:"):
            logger.warning(
                "Refusing to write upload source into shared FAISS: %s", src
            )
            return 0
        if any(_is_upload_source(d.metadata) for d in documents):
            logger.warning("Refusing to write pdf_upload docs into shared FAISS")
            return 0

        with _faiss_write_lock:
            if src and self.has_source(str(src)):
                logger.info("Skipping embed — source already indexed: %s", src)
                return 0

            logger.info("Embedding %s new documents into FAISS (%s)", len(documents), src)
            self._vector_store.add_documents(documents)
            self._vector_store.save_local(str(self.vector_store_path))
            logger.info(
                "FAISS updated and saved (%s total vectors)",
                getattr(self._vector_store.index, "ntotal", "?"),
            )
            return len(documents)


class QdrantRetriever(BaseRetriever):
    """Cloud Qdrant-based retriever."""

    def __init__(self) -> None:
        settings = get_settings()
        self.top_k = settings.top_k
        self.collection_name = settings.qdrant_collection

        if not settings.qdrant_url:
            raise ValueError("QDRANT_URL not set in environment")

        try:
            from langchain_qdrant import Qdrant
            from qdrant_client import QdrantClient
        except ImportError as e:
            raise ImportError(
                "Qdrant dependencies missing. Install langchain-qdrant and qdrant-client."
            ) from e

        logger.info("Connecting to Qdrant at %s", settings.qdrant_url)
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        embeddings = get_cached_embeddings()
        self._vector_store = Qdrant(
            client=self._client,
            collection_name=self.collection_name,
            embeddings=embeddings,
        )
        logger.info(
            "Qdrant retriever initialized for collection: %s", self.collection_name
        )

    def retrieve(self, query: str, k: int | None = None) -> List[Tuple[Document, float]]:
        k = k or self.top_k
        fetch_k = max(k * 2, k + 4)
        results = self._vector_store.similarity_search_with_score(query, k=fetch_k)
        cleaned = _without_uploads(results)[:k]
        logger.info(
            "Qdrant: Retrieved %s documents (%s after excluding uploads)",
            len(results),
            len(cleaned),
        )
        return cleaned


class Retriever:
    """Unified retriever that auto-selects backend and runs advanced RAG pipeline."""

    def __init__(self) -> None:
        settings = get_settings()
        if settings.vector_store_type == "qdrant":
            self._retriever: BaseRetriever = QdrantRetriever()
        else:
            self._retriever = FAISSRetriever()

        from core.rag_pipeline import RAGPipeline

        self._rag_pipeline = RAGPipeline(self._retriever)

    def retrieve(self, query: str, k: int | None = None) -> List[Tuple[Document, float]]:
        """Retrieve using advanced RAG pipeline (rewrite + retrieve + rerank)."""
        _, documents, _ = self._rag_pipeline.process(query, k=k)
        return documents

    def retrieve_with_meta(
        self, query: str, k: int | None = None
    ) -> Tuple[List[Tuple[Document, float]], dict]:
        """Retrieve and return pipeline metadata (rewrite, scores)."""
        _, documents, meta = self._rag_pipeline.process(query, k=k)
        return documents, meta

    def retrieve_for_source(
        self, query: str, source: str, k: int = 3
    ) -> List[Tuple[Document, float]]:
        """Retrieve from the ephemeral upload index (never the PubMed corpus)."""
        from core.upload_index import retrieve_upload

        document_id = source
        if source.startswith("upload:"):
            document_id = source.split(":", 1)[1]
        return retrieve_upload(document_id, query, k=k)

    def index_upload(self, document_id: str, documents: List[Document]) -> int:
        """Index an uploaded PDF in memory only."""
        from core.upload_index import index_upload_documents

        return index_upload_documents(document_id, documents)

    def drop_upload(self, document_id: str) -> None:
        from core.upload_index import drop_upload_index

        drop_upload_index(document_id)

    def get_context(self, query: str, k: int | None = None) -> str:
        """Get formatted context using advanced RAG pipeline."""
        return format_context(self.retrieve(query, k=k))

    def add_documents(self, documents: List[Document], source: str | None = None) -> int:
        """Persist new documents into the active vector store (FAISS local only).

        Upload sources must use index_upload() — they are refused here.
        """
        src = source or (
            (documents[0].metadata or {}).get("source") if documents else None
        )
        if src and str(src).startswith("upload:"):
            logger.warning("Use index_upload() for upload sources; refusing shared write")
            return 0
        base = self._retriever
        if hasattr(base, "add_documents"):
            return base.add_documents(documents, source=source)
        logger.warning("add_documents not supported for this vector backend")
        return 0

    def has_source(self, source: str) -> bool:
        base = self._retriever
        if hasattr(base, "has_source"):
            return base.has_source(source)
        return False


_shared_retriever: Retriever | None = None


def get_shared_retriever() -> Retriever:
    """Process-wide Retriever singleton (used by routes + selection analyzer)."""
    global _shared_retriever
    if _shared_retriever is None:
        _shared_retriever = Retriever()
    return _shared_retriever

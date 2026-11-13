"""Free HuggingFace embeddings."""
from functools import lru_cache
import logging

from langchain_community.embeddings import HuggingFaceEmbeddings

from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_cached_embeddings():
    """Get cached HuggingFace embedding model (completely free)."""
    try:
        import sentence_transformers  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "sentence-transformers is not installed; falling back to built-in seed retriever."
        ) from e

    settings = get_settings()
    logger.info(
        "Using HuggingFace embeddings: %s (normalize=%s)",
        settings.embedding_model,
        settings.normalize_embeddings,
    )
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": settings.normalize_embeddings},
    )

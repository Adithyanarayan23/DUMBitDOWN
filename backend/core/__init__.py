"""Core functionality for DumbItDown."""

__all__ = [
    "Retriever",
    "Simplifier",
    "QAChain",
    "ConversationManager",
    "get_cached_embeddings",
]


def __getattr__(name: str):
    if name == "Retriever":
        from .retrieval import Retriever
        return Retriever
    if name == "Simplifier":
        from .simplification import Simplifier
        return Simplifier
    if name == "QAChain":
        from .simplification import QAChain
        return QAChain
    if name == "ConversationManager":
        from .conversation import ConversationManager
        return ConversationManager
    if name == "get_cached_embeddings":
        from .embeddings import get_cached_embeddings
        return get_cached_embeddings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

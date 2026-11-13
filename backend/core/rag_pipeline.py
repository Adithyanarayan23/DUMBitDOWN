"""Advanced RAG pipeline with query rewriting and reranking (always-on)."""
import logging
from typing import List, Tuple

from langchain_core.documents import Document
import google.generativeai as genai

from config import get_settings
from core.llm import safe_generate_text

logger = logging.getLogger(__name__)


QUERY_REWRITE_PROMPT = """You are a search query optimizer for academic research retrieval.

Original query: {query}

Your task: Rewrite this query to improve retrieval of relevant academic papers.

Rules:
- Expand abbreviations and technical terms
- Add related concepts that might appear in papers
- Keep the core meaning intact
- Return ONLY the optimized query, no explanation

Optimized query:"""


class QueryRewriter:
    """Expand queries for better retrieval."""

    def rewrite(self, query: str) -> str:
        """Expand and optimize the search query."""
        # Skip very short queries and long pasted passages (demo latency)
        if len(query) < 20 or len(query) >= 200:
            return query

        try:
            prompt = QUERY_REWRITE_PROMPT.format(query=query)
            rewritten = safe_generate_text(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            logger.info(
                "Query rewritten: '%s...' -> '%s...'",
                query[:50],
                rewritten[:50],
            )
            return rewritten
        except Exception as e:
            logger.error("Query rewriting failed: %s", e)
            return query


class HeuristicReranker:
    """Heuristic reranker. FAISS L2 distances are lower-is-better; convert to similarity."""

    def __init__(self):
        settings = get_settings()
        self.top_n = settings.rerank_top_n

    def rerank(
        self,
        query: str,
        docs_with_scores: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Rerank documents; returned scores are similarities (higher = better)."""
        if len(docs_with_scores) <= self.top_n:
            return [
                (doc, 1.0 / (1.0 + float(distance)))
                for doc, distance in docs_with_scores
            ]

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        reranked = []
        for doc, distance in docs_with_scores:
            content = doc.page_content.lower()
            base_sim = 1.0 / (1.0 + float(distance))

            term_matches = sum(1 for term in query_terms if term in content)
            term_bonus = term_matches * 0.01

            length_penalty = -0.05 if len(doc.page_content) < 100 else 0.0
            final_score = base_sim + term_bonus + length_penalty
            reranked.append((doc, final_score, base_sim))

        reranked.sort(key=lambda x: x[1], reverse=True)
        # Return similarity (not L2) for contribution percentages
        result = [(doc, base_sim) for doc, _, base_sim in reranked[: self.top_n]]
        logger.info("Heuristic reranked %s docs to top %s", len(docs_with_scores), len(result))
        return result


class RAGPipeline:
    """Complete RAG pipeline: Query → Rewrite → Retrieve → Rerank."""

    def __init__(self, retriever):
        self.retriever = retriever
        self.query_rewriter = QueryRewriter()
        self.reranker = HeuristicReranker()

    def process(self, query: str, k: int = None) -> Tuple[str, List[Tuple[Document, float]], dict]:
        """
        Execute full RAG pipeline.

        Returns:
            Tuple of (original_query, reranked_documents with similarity scores, pipeline_meta)
        """
        original_query = query
        rewritten_query = self.query_rewriter.rewrite(query)
        search_query = rewritten_query if len(original_query) > 30 else original_query
        # Base retriever returns L2 distances
        docs = self.retriever.retrieve(search_query, k=k)
        reranked_docs = self.reranker.rerank(original_query, docs)
        pipeline_meta = {
            "original_query": original_query[:200],
            "rewritten_query": rewritten_query
            if rewritten_query != original_query
            else None,
            "search_query": search_query[:200],
            "retrieved_count": len(docs),
            "reranked_count": len(reranked_docs),
            "top_scores": [
                round(float(score), 4) for _, score in reranked_docs
            ],
        }
        return original_query, reranked_docs, pipeline_meta

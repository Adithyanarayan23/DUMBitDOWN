"""Enhanced citation system with full paper metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional, List


_BAD_TITLES = {"", "untitled", "unknown title", "untitled source", "unknown"}


@dataclass
class Citation:
    """Full citation information for a paper."""

    id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    relevance_score: float = 0.0
    contribution_percentage: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def formatted_citation(self) -> str:
        if not self.authors:
            author_str = None
        elif len(self.authors) == 1:
            author_str = self.authors[0]
        elif len(self.authors) == 2:
            author_str = f"{self.authors[0]} & {self.authors[1]}"
        else:
            author_str = f"{self.authors[0]} et al."

        year_str = f" ({self.year})" if self.year else ""
        if author_str:
            return f"{author_str}{year_str}. {self.title}."
        return f"{self.title}{year_str}."

    @property
    def pubmed_url(self) -> Optional[str]:
        if self.pmid:
            return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        return None

    @property
    def arxiv_url(self) -> Optional[str]:
        if self.arxiv_id:
            return f"https://arxiv.org/abs/{self.arxiv_id}"
        return None


class CitationFormatter:
    """Format citations with contribution analysis."""

    @staticmethod
    def format_with_contribution(citations: List[Citation]) -> dict:
        if not citations:
            return {"sources": [], "total": 0, "primary_source": None}

        total_score = sum(c.relevance_score for c in citations)
        sources = []
        for citation in citations:
            if total_score > 0:
                contribution = (citation.relevance_score / total_score) * 100
            else:
                contribution = 100 / len(citations)

            pct = round(contribution, 1)
            citation.contribution_percentage = pct
            authors_display = (
                ", ".join(citation.authors) if citation.authors else "—"
            )
            apa = citation.formatted_citation

            scholar_url = None
            if citation.title and citation.title.lower() not in _BAD_TITLES:
                from urllib.parse import quote

                scholar_url = (
                    f"https://scholar.google.com/scholar?q={quote(citation.title)}"
                )

            snippet = None
            if citation.abstract:
                snippet = (
                    citation.abstract[:300] + "..."
                    if len(citation.abstract) > 300
                    else citation.abstract
                )

            sources.append(
                {
                    "id": citation.id,
                    "title": citation.title,
                    "authors": citation.authors,
                    "authors_display": authors_display,
                    "year": citation.year,
                    "journal": citation.journal,
                    "formatted_citation": apa,
                    "apa_citation": apa,
                    "pmid": citation.pmid,
                    "arxiv_id": citation.arxiv_id,
                    "doi": citation.doi,
                    "urls": {
                        "pubmed": citation.pubmed_url,
                        "arxiv": citation.arxiv_url,
                        "doi": f"https://doi.org/{citation.doi}" if citation.doi else None,
                        "pdf": citation.pdf_url,
                        "main": citation.url,
                        "scholar": scholar_url,
                    },
                    "relevance_score": round(citation.relevance_score, 4),
                    "contribution_percentage": pct,
                    "contribution": pct,
                    "snippet": snippet,
                    "abstract_preview": (
                        citation.abstract[:200] + "..."
                        if citation.abstract and len(citation.abstract) > 200
                        else citation.abstract
                    ),
                }
            )

        return {
            "sources": sources,
            "total": len(sources),
            "primary_source": sources[0] if sources else None,
        }

    @staticmethod
    def generate_bibliography(citations: List[Citation], style: str = "apa") -> str:
        if style == "apa":
            return "\n\n".join([c.formatted_citation for c in citations])
        lines = []
        for i, c in enumerate(citations, 1):
            lines.append(f"[{i}] {c.formatted_citation}")
        return "\n".join(lines)


def _title_from_content(page_content: str) -> Optional[str]:
    if not page_content:
        return None
    match = re.search(r"Title:\s*(.+)", page_content)
    if match:
        title = match.group(1).strip()
        for sep in ("\n\n", "\nAbstract:", "\nArticle:"):
            if sep in title:
                title = title.split(sep)[0].strip()
        if title and title.lower() not in _BAD_TITLES:
            return title
    return None


def _snippet_title(page_content: str, max_len: int = 90) -> Optional[str]:
    if not page_content:
        return None
    cleaned = " ".join(page_content.strip().split())
    # Skip latex-noise heavy openings
    if cleaned.count("\\") > 8 or cleaned.count("@xmath") > 2:
        # Try to find a readable sentence later in the chunk
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        for part in parts:
            if part.count("\\") < 3 and len(part) > 30 and "@xmath" not in part:
                cleaned = part
                break
        else:
            return None
    if not cleaned:
        return None
    return cleaned[:max_len] + ("…" if len(cleaned) > max_len else "")


def extract_citation_from_metadata(
    metadata: dict,
    page_content: str | None = None,
) -> Citation:
    """Extract citation info from document metadata / content fallback."""
    authors = metadata.get("authors") or metadata.get("author") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]

    year = metadata.get("year")
    if not year and metadata.get("date"):
        try:
            year = int(str(metadata["date"])[:4])
        except (ValueError, IndexError, TypeError):
            year = None

    title = (metadata.get("title") or "").strip()
    if title.lower() in _BAD_TITLES:
        title = ""

    if not title and page_content:
        parsed = _title_from_content(page_content)
        if parsed:
            title = parsed

    if not title and page_content:
        snip = _snippet_title(page_content)
        if snip:
            title = snip

    if not title:
        source = str(metadata.get("source") or metadata.get("id") or "source")
        # upload:foo.pdf → use filename; paper_974 → "Related paper 974"
        if source.startswith("upload:"):
            title = source.split(":", 1)[1]
        elif source.startswith("paper_"):
            title = f"Related paper {source.replace('paper_', '')}"
        else:
            title = source

    abstract = metadata.get("abstract") or metadata.get("snippet")
    if not abstract and page_content:
        cleaned = page_content.strip()
        abstract = cleaned[:300] + ("..." if len(cleaned) > 300 else "")

    return Citation(
        id=str(metadata.get("id") or metadata.get("source") or "unknown"),
        title=title,
        authors=authors if isinstance(authors, list) else [],
        year=year,
        journal=metadata.get("journal")
        if metadata.get("journal") not in ("Unknown Section", None, "")
        else None,
        volume=metadata.get("volume"),
        issue=metadata.get("issue"),
        pages=metadata.get("pages"),
        doi=metadata.get("doi"),
        pmid=metadata.get("pmid"),
        pmcid=metadata.get("pmcid"),
        arxiv_id=metadata.get("arxiv_id"),
        url=metadata.get("url"),
        pdf_url=metadata.get("pdf_url"),
        abstract=abstract,
        keywords=metadata.get("keywords", []) or [],
        relevance_score=float(metadata.get("score", 0.0) or 0.0),
    )

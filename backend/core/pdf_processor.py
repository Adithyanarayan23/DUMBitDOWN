"""PDF processing and text extraction using PyMuPDF."""
import io
import re
from dataclasses import dataclass
from typing import Optional, List
import logging

import fitz  # PyMuPDF
from langchain_core.documents import Document
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class PDFMetadata:
    """Extracted PDF metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    format: Optional[str] = None
    encryption: Optional[str] = None
    num_pages: int = 0


@dataclass
class ProcessedPDF:
    """Processed PDF with extracted content and metadata."""
    metadata: PDFMetadata
    documents: List[Document]  # Chunked documents ready for vector store
    full_text: str  # Full extracted text
    chunks: List[str]  # Individual chunks
    enrichment: object | None = None  # Optional EnrichmentResult


class PDFProcessor:
    """Process PDFs and extract text for vector storage."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def process_and_enrich(
        self,
        pdf_bytes: bytes,
        source_name: str,
        document_id: str | None = None,
    ) -> ProcessedPDF:
        """
        Single-pass PDF open: text extraction, tables, figures, quality, and chunks.
        """
        from core.pdf_enrichment import (
            _extract_figures,
            _extract_tables,
            _text_blocks_with_bbox,
            EnrichmentResult,
            suppress_tables_inside_figures,
        )

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = self._extract_metadata(doc)
            metadata.num_pages = len(doc)

            raw_page_texts: list[str] = []
            page_texts: list[dict] = []
            tables: list[dict] = []
            figures: list[dict] = []
            full_parts: list[str] = []
            total_chars = 0

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text() or ""
                raw_page_texts.append(text)
                cleaned = self._clean_text(text)
                page_idx = page_num + 1
                page_texts.append({"page": page_idx, "text": cleaned})
                full_parts.append(f"\n\n--- Page {page_idx} ---\n\n{cleaned}")
                total_chars += len(cleaned)

                blocks = _text_blocks_with_bbox(page)
                tables.extend(_extract_tables(page, page_idx, blocks))
                figures.extend(_extract_figures(page, page_idx, blocks))

            doc.close()

            tables = suppress_tables_inside_figures(tables, figures)

            if not metadata.title or metadata.title.strip() in ("", "Untitled", "Unknown"):
                inferred = self._infer_title_from_pages(raw_page_texts)
                if inferred:
                    metadata.title = inferred
            if not metadata.author:
                inferred_author = self._infer_author_from_pages(raw_page_texts)
                if inferred_author:
                    metadata.author = inferred_author

            full_text = self._clean_text("\n".join(full_parts).strip())
            chunks = self.text_splitter.split_text(full_text)
            title = metadata.title or source_name
            source_key = (
                f"upload:{document_id}" if document_id else f"upload:{source_name}"
            )
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "id": f"{source_key}:{i}",
                        "source": source_key,
                        "document_id": document_id,
                        "title": title,
                        "authors": metadata.author or "",
                        "author": metadata.author,
                        "page": self._extract_page_number(chunk),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "type": "pdf_upload",
                        "filename": source_name,
                        "snippet": chunk[:300],
                    },
                )
                for i, chunk in enumerate(chunks)
            ]

            num_pages = max(len(page_texts), 1)
            avg_chars = total_chars / num_pages
            enrichment = EnrichmentResult(
                page_texts=page_texts,
                tables=tables,
                figures=figures,
                quality={
                    "scanned_risk": avg_chars < 100,
                    "avg_chars_per_page": round(avg_chars, 1),
                    "table_count": len(tables),
                    "figure_count": len(figures),
                    "enrichment_status": "ready",
                    "index_status": "pending",
                },
                full_text=full_text,
            )

            logger.info(
                "Processed+enriched PDF '%s': %s pages, %s chunks, %s tables, %s figures",
                source_name,
                metadata.num_pages,
                len(chunks),
                len(tables),
                len(figures),
            )
            return ProcessedPDF(
                metadata=metadata,
                documents=documents,
                full_text=full_text,
                chunks=chunks,
                enrichment=enrichment,
            )
        except Exception as e:
            logger.error("Error processing PDF %s: %s", source_name, e)
            raise ValueError(f"Failed to process PDF: {e}") from e

    def process_text_fast(
        self,
        pdf_bytes: bytes,
        source_name: str,
        document_id: str | None = None,
    ) -> ProcessedPDF:
        """
        Fast path: text + metadata + chunks only (no tables/figures).
        Used so the reader can open before enrichment finishes.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = self._extract_metadata(doc)
            metadata.num_pages = len(doc)

            raw_page_texts: list[str] = []
            page_texts: list[dict] = []
            full_parts: list[str] = []
            total_chars = 0

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text() or ""
                raw_page_texts.append(text)
                cleaned = self._clean_text(text)
                page_idx = page_num + 1
                page_texts.append({"page": page_idx, "text": cleaned})
                full_parts.append(f"\n\n--- Page {page_idx} ---\n\n{cleaned}")
                total_chars += len(cleaned)

            doc.close()

            if not metadata.title or metadata.title.strip() in ("", "Untitled", "Unknown"):
                inferred = self._infer_title_from_pages(raw_page_texts)
                if inferred:
                    metadata.title = inferred
            if not metadata.author:
                inferred_author = self._infer_author_from_pages(raw_page_texts)
                if inferred_author:
                    metadata.author = inferred_author

            full_text = self._clean_text("\n".join(full_parts).strip())
            chunks = self.text_splitter.split_text(full_text)
            title = metadata.title or source_name
            source_key = (
                f"upload:{document_id}" if document_id else f"upload:{source_name}"
            )
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "id": f"{source_key}:{i}",
                        "source": source_key,
                        "document_id": document_id,
                        "title": title,
                        "authors": metadata.author or "",
                        "author": metadata.author,
                        "page": self._extract_page_number(chunk),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "type": "pdf_upload",
                        "filename": source_name,
                        "snippet": chunk[:300],
                    },
                )
                for i, chunk in enumerate(chunks)
            ]

            num_pages = max(len(page_texts), 1)
            avg_chars = total_chars / num_pages
            from core.pdf_enrichment import EnrichmentResult

            enrichment = EnrichmentResult(
                page_texts=page_texts,
                tables=[],
                figures=[],
                quality={
                    "scanned_risk": avg_chars < 100,
                    "avg_chars_per_page": round(avg_chars, 1),
                    "table_count": 0,
                    "figure_count": 0,
                    "enrichment_status": "pending",
                    "index_status": "pending",
                },
                full_text=full_text,
            )

            logger.info(
                "Fast-processed PDF '%s': %s pages, %s chunks (enrichment deferred)",
                source_name,
                metadata.num_pages,
                len(chunks),
            )
            return ProcessedPDF(
                metadata=metadata,
                documents=documents,
                full_text=full_text,
                chunks=chunks,
                enrichment=enrichment,
            )
        except Exception as e:
            logger.error("Error fast-processing PDF %s: %s", source_name, e)
            raise ValueError(f"Failed to process PDF: {e}") from e

    def process_pdf(
        self,
        pdf_bytes: bytes,
        source_name: str,
        document_id: str | None = None,
    ) -> ProcessedPDF:
        """Process a PDF file and extract text (no table/figure enrichment)."""
        return self.process_and_enrich(pdf_bytes, source_name, document_id)

    def documents_from_stored(
        self,
        *,
        chunks: list[str],
        source_name: str,
        document_id: str,
        title: str | None = None,
        author: str | None = None,
    ) -> list[Document]:
        """Rebuild LangChain documents from stored chunks (no PDF re-parse)."""
        source_key = f"upload:{document_id}"
        display_title = title or source_name
        docs: list[Document] = []
        for i, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "id": f"{source_key}:{i}",
                        "source": source_key,
                        "document_id": document_id,
                        "title": display_title,
                        "authors": author or "",
                        "author": author,
                        "page": self._extract_page_number(chunk),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "type": "pdf_upload",
                        "filename": source_name,
                        "snippet": chunk[:300],
                    },
                )
            )
        return docs

    def _extract_metadata(self, doc: fitz.Document) -> PDFMetadata:
        """Extract metadata from PDF."""
        pdf_metadata = doc.metadata or {}
        title = (pdf_metadata.get("title") or "").strip() or None
        author = (pdf_metadata.get("author") or "").strip() or None

        return PDFMetadata(
            title=title,
            author=author,
            subject=pdf_metadata.get("subject"),
            keywords=pdf_metadata.get("keywords"),
            creator=pdf_metadata.get("creator"),
            producer=pdf_metadata.get("producer"),
            format=pdf_metadata.get("format"),
            encryption=pdf_metadata.get("encryption"),
        )

    def _infer_title_from_pages(self, page_texts: list[str]) -> Optional[str]:
        """Guess paper title from the first page's prominent lines."""
        if not page_texts:
            return None
        first = page_texts[0]
        lines = [ln.strip() for ln in first.splitlines() if ln.strip()]
        # Drop very short / boilerplate lines
        skip = re.compile(
            r"^(arxiv|doi|http|www\.|abstract|introduction|page\s*\d+|"
            r"preprint|manuscript|copyright|all rights|vol\.|volume)",
            re.I,
        )
        candidates = []
        for ln in lines[:25]:
            if len(ln) < 12 or len(ln) > 200:
                continue
            if skip.search(ln):
                continue
            if re.match(r"^[\d\W]+$", ln):
                continue
            # Prefer title-case / mixed-case research titles over all-caps headers
            candidates.append(ln)

        if not candidates:
            return None

        # Longest early line is a decent heuristic for title
        best = max(candidates[:8], key=len)
        return best

    def _infer_author_from_pages(self, page_texts: list[str]) -> Optional[str]:
        if not page_texts:
            return None
        lines = [ln.strip() for ln in page_texts[0].splitlines() if ln.strip()]
        # Common pattern: names with commas / "and" near top after title
        for ln in lines[1:12]:
            if 8 < len(ln) < 120 and (
                "," in ln or " and " in ln.lower() or re.search(r"\b[A-Z]\.\s*[A-Z]", ln)
            ):
                if not re.search(r"abstract|university|department|email|@", ln, re.I):
                    # Avoid lines that look like full affiliations
                    if ln.count(",") <= 6:
                        return ln
        return None

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\x0c", "", text)
        return text.strip()

    def _extract_page_number(self, chunk: str) -> Optional[int]:
        match = re.search(r"--- Page (\d+) ---", chunk)
        if match:
            return int(match.group(1))
        return None

    def extract_text_only(self, pdf_bytes: bytes) -> str:
        """Extract full text without chunking (for quick preview)."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return self._clean_text(text)
        except Exception as e:
            logger.error("Error extracting text: %s", e)
            raise ValueError(f"Failed to extract text: {e}") from e


def validate_pdf(file_bytes: bytes) -> bool:
    """Validate that bytes are a valid PDF."""
    return file_bytes.startswith(b"%PDF")

"""SQLite-backed store for uploaded PDF document sessions."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class StoredDocument:
    id: str
    filename: str
    file_hash: str
    pdf_path: str
    num_pages: int
    metadata: dict
    tables: list[dict]
    figures: list[dict]
    quality: dict
    created_at: str
    expires_at: str
    page_texts: Optional[list[dict]] = None  # None → paginated via document_pages
    chunks: list[str] = field(default_factory=list)
    full_text: str = ""


class DocumentStore:
    """Persist uploaded PDFs + enriched manifests with TTL cleanup."""

    def __init__(self) -> None:
        settings = get_settings()
        self.db_path = Path(settings.documents_db_path)
        self.uploads_dir = Path(settings.uploads_dir)
        self.ttl_hours = settings.document_ttl_hours
        self.max_inline_pages = settings.max_inline_pages
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_hash TEXT,
                    pdf_path TEXT NOT NULL,
                    num_pages INTEGER NOT NULL,
                    metadata TEXT,
                    tables TEXT NOT NULL,
                    figures TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    page_texts TEXT,
                    chunks TEXT,
                    full_text TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_pages (
                    document_id TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    PRIMARY KEY (document_id, page),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
                """
            )
            conn.commit()
        logger.info("Document database initialized at %s", self.db_path)

    def save_pdf_bytes(self, document_id: str, pdf_bytes: bytes) -> Path:
        path = self.uploads_dir / f"{document_id}.pdf"
        path.write_bytes(pdf_bytes)
        return path

    def create(
        self,
        *,
        filename: str,
        pdf_bytes: bytes,
        num_pages: int,
        metadata: dict,
        tables: list[dict],
        figures: list[dict],
        quality: dict,
        page_texts: list[dict],
        chunks: list[str] | None = None,
        full_text: str = "",
        document_id: str | None = None,
    ) -> StoredDocument:
        doc_id = document_id or str(uuid.uuid4())
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        pdf_path = str(self.save_pdf_bytes(doc_id, pdf_bytes))
        now = datetime.utcnow()
        expires = now + timedelta(hours=self.ttl_hours)

        inline = num_pages <= self.max_inline_pages
        page_texts_json = json.dumps(page_texts) if inline else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, filename, file_hash, pdf_path, num_pages, metadata,
                    tables, figures, quality, page_texts, chunks, full_text,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    filename,
                    file_hash,
                    pdf_path,
                    num_pages,
                    json.dumps(metadata),
                    json.dumps(tables),
                    json.dumps(figures),
                    json.dumps(quality),
                    page_texts_json,
                    json.dumps(chunks or []),
                    full_text,
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            if not inline:
                for pt in page_texts:
                    conn.execute(
                        """
                        INSERT INTO document_pages (document_id, page, text)
                        VALUES (?, ?, ?)
                        """,
                        (doc_id, pt["page"], pt["text"]),
                    )
            conn.commit()

        logger.info("Stored document %s (%s pages)", doc_id, num_pages)
        return StoredDocument(
            id=doc_id,
            filename=filename,
            file_hash=file_hash,
            pdf_path=pdf_path,
            num_pages=num_pages,
            metadata=metadata,
            tables=tables,
            figures=figures,
            quality=quality,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            page_texts=page_texts if inline else None,
            chunks=chunks or [],
            full_text=full_text,
        )

    def get(self, document_id: str) -> Optional[StoredDocument]:
        self.cleanup_expired()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            if not row:
                return None
            if row["expires_at"] < datetime.utcnow().isoformat():
                self.delete(document_id)
                return None

            page_texts = None
            if row["page_texts"]:
                page_texts = json.loads(row["page_texts"])

            return StoredDocument(
                id=row["id"],
                filename=row["filename"],
                file_hash=row["file_hash"] or "",
                pdf_path=row["pdf_path"],
                num_pages=row["num_pages"],
                metadata=json.loads(row["metadata"] or "{}"),
                tables=json.loads(row["tables"] or "[]"),
                figures=json.loads(row["figures"] or "[]"),
                quality=json.loads(row["quality"] or "{}"),
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                page_texts=page_texts,
                chunks=json.loads(row["chunks"] or "[]"),
                full_text=row["full_text"] or "",
            )

    def get_page_text(self, document_id: str, page: int) -> Optional[str]:
        doc = self.get(document_id)
        if not doc:
            return None
        if doc.page_texts:
            for pt in doc.page_texts:
                if pt.get("page") == page:
                    return pt.get("text") or ""
            return None
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT text FROM document_pages
                WHERE document_id = ? AND page = ?
                """,
                (document_id, page),
            ).fetchone()
            return row[0] if row else None

    def get_table(self, document_id: str, table_id: str) -> Optional[dict]:
        doc = self.get(document_id)
        if not doc:
            return None
        for t in doc.tables:
            if t.get("id") == table_id:
                return t
        return None

    def get_figure(self, document_id: str, figure_id: str) -> Optional[dict]:
        doc = self.get(document_id)
        if not doc:
            return None
        for f in doc.figures:
            if f.get("id") == figure_id:
                return f
        return None

    def read_pdf_bytes(self, document_id: str) -> Optional[bytes]:
        doc = self.get(document_id)
        if not doc:
            return None
        path = Path(doc.pdf_path)
        if not path.exists():
            return None
        return path.read_bytes()

    def update_enrichment(
        self,
        document_id: str,
        *,
        tables: list[dict],
        figures: list[dict],
        quality: dict,
    ) -> Optional[StoredDocument]:
        """Patch tables/figures/quality after background enrichment."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE documents
                SET tables = ?, figures = ?, quality = ?
                WHERE id = ?
                """,
                (
                    json.dumps(tables),
                    json.dumps(figures),
                    json.dumps(quality),
                    document_id,
                ),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        return self.get(document_id)

    def update_quality(
        self, document_id: str, quality: dict
    ) -> Optional[StoredDocument]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE documents SET quality = ? WHERE id = ?",
                (json.dumps(quality), document_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        return self.get(document_id)

    def delete(self, document_id: str) -> bool:
        try:
            from core.upload_index import drop_upload_index

            drop_upload_index(document_id)
        except Exception:
            pass
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT pdf_path FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            conn.execute(
                "DELETE FROM document_pages WHERE document_id = ?", (document_id,)
            )
            cursor = conn.execute(
                "DELETE FROM documents WHERE id = ?", (document_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        if row and row[0]:
            try:
                Path(row[0]).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to delete PDF file for %s", document_id)
        return deleted

    def cleanup_expired(self) -> int:
        now = datetime.utcnow().isoformat()
        removed = 0
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, pdf_path FROM documents WHERE expires_at < ?", (now,)
            ).fetchall()
            for doc_id, pdf_path in rows:
                try:
                    from core.upload_index import drop_upload_index

                    drop_upload_index(doc_id)
                except Exception:
                    pass
                conn.execute(
                    "DELETE FROM document_pages WHERE document_id = ?", (doc_id,)
                )
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                if pdf_path:
                    try:
                        Path(pdf_path).unlink(missing_ok=True)
                    except OSError:
                        pass
                removed += 1
            conn.commit()
        if removed:
            logger.info("Cleaned up %s expired documents", removed)
        return removed

    def to_manifest(self, doc: StoredDocument, *, include_pages: bool = True) -> dict[str, Any]:
        settings = get_settings()
        pages_included = bool(doc.page_texts) and include_pages
        tables_out = []
        for t in doc.tables:
            tables_out.append(
                {
                    "id": t["id"],
                    "page": t["page"],
                    "bbox": t["bbox"],
                    "caption": t.get("caption"),
                    "confidence": t.get("confidence", 0.5),
                    "preview": (t.get("markdown") or "")[
                        : settings.max_table_preview_chars
                    ],
                }
            )
        figures_out = [
            {
                "id": f["id"],
                "page": f["page"],
                "bbox": f["bbox"],
                "caption": f.get("caption"),
                "has_selectable_caption": bool(f.get("caption")),
                "render_mode": f.get("render_mode", "image"),
            }
            for f in doc.figures
        ]
        preview = doc.full_text[:1000]
        if len(doc.full_text) > 1000:
            preview += "..."

        provider = (settings.llm_provider or "google").strip().lower()
        vision_available = provider == "google"

        quality = dict(doc.quality or {})
        quality.setdefault("enrichment_status", "ready")
        quality.setdefault("index_status", "ready")

        manifest = {
            "document_id": doc.id,
            "filename": doc.filename,
            "metadata": {
                "title": doc.metadata.get("title"),
                "author": doc.metadata.get("author"),
                "pages": doc.num_pages,
                "chunks": len(doc.chunks),
            },
            "quality": quality,
            "tables": tables_out,
            "figures": figures_out,
            "indexed_chunks": quality.get("indexed_chunks", 0),
            "text_preview": preview,
            "pages_included": pages_included,
            "capabilities": {
                "vision": vision_available,
                "llm_provider": provider,
            },
        }
        if pages_included and doc.page_texts:
            manifest["pages"] = doc.page_texts
        return manifest


_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store

"""API routes for text simplification and Q&A."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from core.retrieval import Retriever, format_context
from core.simplification import Simplifier, QAChain
from core.conversation import ConversationManager
from core.citations import CitationFormatter, extract_citation_from_metadata
from core.llm import get_resolved_model_name, resolve_model

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singletons
_retriever: Retriever | None = None
_simplifier: Simplifier | None = None
_qa_chain: QAChain | None = None
_conversation_manager: ConversationManager | None = None
_pdf_processor = None
_retriever_error: str | None = None


def get_retriever() -> Retriever:
    global _retriever, _retriever_error
    if _retriever is None:
        try:
            from core.retrieval import get_shared_retriever

            _retriever = get_shared_retriever()
            _retriever_error = None
        except Exception as e:
            _retriever_error = str(e)
            raise
    return _retriever


def get_simplifier() -> Simplifier:
    global _simplifier
    if _simplifier is None:
        _simplifier = Simplifier()
    return _simplifier


def get_qa_chain() -> QAChain:
    global _qa_chain
    if _qa_chain is None:
        _qa_chain = QAChain()
    return _qa_chain


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


def get_pdf_processor():
    global _pdf_processor
    if _pdf_processor is None:
        from core.pdf_processor import PDFProcessor
        _pdf_processor = PDFProcessor()
    return _pdf_processor


def _validate_pdf(contents: bytes) -> bool:
    from core.pdf_processor import validate_pdf
    return validate_pdf(contents)


def _docs_to_results(docs) -> list[dict]:
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata or {},
            "score": float(score),
        }
        for doc, score in docs
    ]


def _docs_to_citations(docs) -> dict:
    citations = [
        extract_citation_from_metadata(
            {**(doc.metadata or {}), "score": score},
            page_content=doc.page_content,
        )
        for doc, score in docs
    ]
    return CitationFormatter.format_with_contribution(citations)


def _client_error(message: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


class SearchRequest(BaseModel):
    query: str
    question: Optional[str] = None
    k: Optional[int] = 5
    conversation_id: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    context: str
    simplified_text: str
    results: list[dict]
    citations: dict
    technical_terms: list[dict] = Field(default_factory=list)
    answer: Optional[str] = None
    conversation_id: str
    pipeline: dict = Field(default_factory=dict)


class QARequest(BaseModel):
    query: str
    question: str
    k: Optional[int] = 5
    conversation_id: Optional[str] = None


class QAResponse(BaseModel):
    query: str
    question: str
    context: str
    simplified_text: str
    answer: str
    technical_terms: list[dict] = Field(default_factory=list)
    citations: dict = Field(default_factory=dict)
    conversation_id: str
    pipeline: dict = Field(default_factory=dict)


class FollowUpRequest(BaseModel):
    conversation_id: str
    question: str
    k: Optional[int] = 5


class FollowUpResponse(BaseModel):
    question: str
    answer: str
    context: str
    citations: dict = Field(default_factory=dict)
    technical_terms: list[dict] = Field(default_factory=list)
    pipeline: dict = Field(default_factory=dict)


class ConversationListResponse(BaseModel):
    conversations: list[dict]


def _sse(event: str, data: dict) -> str:
    payload = json.dumps({"event": event, **data}, default=str)
    return f"data: {payload}\n\n"


def _build_pipeline(meta: dict, citation_data: dict) -> dict:
    sources = (citation_data or {}).get("sources") or []
    return {
        **(meta or {}),
        "model": get_resolved_model_name(),
        "contributions": [
            {
                "title": s.get("title"),
                "contribution": s.get("contribution") or s.get("contribution_percentage"),
            }
            for s in sources
        ],
    }


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Simplify complex text and optionally answer a question."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        cm = get_conversation_manager()
        if request.conversation_id:
            conversation_id = request.conversation_id
            cm.store.add_message(
                conversation_id, "user", request.query, {"type": "input"}
            )
            conv_context = cm.get_conversation_context(conversation_id)
        else:
            conversation_id = cm.start_conversation(request.query)
            conv_context = ""

        docs, pipeline_meta = get_retriever().retrieve_with_meta(
            request.query, k=request.k
        )
        vector_context = format_context(docs)
        full_context = (
            f"{conv_context}\n\n{vector_context}" if conv_context else vector_context
        )

        simplify_result = get_simplifier().simplify(request.query, full_context)
        results = _docs_to_results(docs)
        citation_data = _docs_to_citations(docs)
        pipeline = _build_pipeline(pipeline_meta, citation_data)

        cm.add_assistant_response(conversation_id, simplify_result.text, results)

        answer = None
        if request.question:
            answer = get_qa_chain().answer(
                request.question,
                request.query,
                full_context,
                simplify_result.text,
            )
            cm.add_qa_pair(conversation_id, request.question, answer)

        return SearchResponse(
            query=request.query,
            context=vector_context,
            simplified_text=simplify_result.text,
            results=results,
            citations=citation_data,
            technical_terms=simplify_result.technical_terms,
            answer=answer,
            conversation_id=conversation_id,
            pipeline=pipeline,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Search failed")
        raise _client_error("Simplification failed. Please try again.")


@router.post("/search/stream")
async def search_stream(request: SearchRequest):
    """SSE: meta (citations) → token* → terms → done."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    def event_gen():
        try:
            cm = get_conversation_manager()
            if request.conversation_id:
                conversation_id = request.conversation_id
                cm.store.add_message(
                    conversation_id, "user", request.query, {"type": "input"}
                )
                conv_context = cm.get_conversation_context(conversation_id)
            else:
                conversation_id = cm.start_conversation(request.query)
                conv_context = ""

            docs, pipeline_meta = get_retriever().retrieve_with_meta(
                request.query, k=request.k
            )
            vector_context = format_context(docs)
            full_context = (
                f"{conv_context}\n\n{vector_context}" if conv_context else vector_context
            )
            results = _docs_to_results(docs)
            citation_data = _docs_to_citations(docs)
            pipeline = _build_pipeline(pipeline_meta, citation_data)

            yield _sse(
                "meta",
                {
                    "conversation_id": conversation_id,
                    "citations": citation_data,
                    "pipeline": pipeline,
                    "query": request.query,
                },
            )

            simplify_result = None
            for kind, payload in get_simplifier().simplify_stream(
                request.query, full_context
            ):
                if kind == "token":
                    yield _sse("token", {"text": payload})
                elif kind == "result":
                    simplify_result = payload

            if simplify_result is None:
                yield _sse("error", {"detail": "Empty simplification"})
                return

            cm.add_assistant_response(
                conversation_id, simplify_result.text, results
            )
            yield _sse("terms", {"technical_terms": simplify_result.technical_terms})
            yield _sse(
                "done",
                {
                    "simplified_text": simplify_result.text,
                    "conversation_id": conversation_id,
                    "citations": citation_data,
                    "technical_terms": simplify_result.technical_terms,
                    "pipeline": pipeline,
                    "context": vector_context,
                },
            )
        except Exception:
            logger.exception("Search stream failed")
            yield _sse("error", {"detail": "Simplification failed. Please try again."})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/qa", response_model=QAResponse)
async def qa(request: QARequest) -> QAResponse:
    """Answer a specific question about the text."""
    if not request.query.strip() or not request.question.strip():
        raise HTTPException(
            status_code=400, detail="Both query and question required"
        )

    try:
        cm = get_conversation_manager()
        if request.conversation_id:
            conversation_id = request.conversation_id
            conv_context = cm.get_conversation_context(conversation_id)
        else:
            conversation_id = cm.start_conversation(request.query)
            conv_context = ""

        docs, pipeline_meta = get_retriever().retrieve_with_meta(
            request.query, k=request.k
        )
        vector_context = format_context(docs)
        full_context = (
            f"{conv_context}\n\n{vector_context}" if conv_context else vector_context
        )

        simplify_result = get_simplifier().simplify(request.query, full_context)
        answer = get_qa_chain().answer(
            request.question,
            request.query,
            full_context,
            simplify_result.text,
        )
        cm.add_qa_pair(conversation_id, request.question, answer)
        citation_data = _docs_to_citations(docs)

        return QAResponse(
            query=request.query,
            question=request.question,
            context=vector_context,
            simplified_text=simplify_result.text,
            answer=answer,
            technical_terms=simplify_result.technical_terms,
            citations=citation_data,
            conversation_id=conversation_id,
            pipeline=_build_pipeline(pipeline_meta, citation_data),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("QA failed")
        raise _client_error("Question answering failed. Please try again.")


@router.post("/followup", response_model=FollowUpResponse)
async def followup(request: FollowUpRequest) -> FollowUpResponse:
    """Ask a follow-up question in an existing conversation."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    cm = get_conversation_manager()
    conversation = cm.store.get_conversation(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        conv_context = cm.get_conversation_context(request.conversation_id)
        original_query = (
            conversation.messages[0].content if conversation.messages else ""
        )

        docs, pipeline_meta = get_retriever().retrieve_with_meta(
            request.question, k=request.k
        )
        vector_context = format_context(docs)
        full_context = f"{conv_context}\n\nRELEVANT DOCUMENTS:\n{vector_context}"

        answer = get_qa_chain().answer(
            request.question,
            original_query,
            full_context,
            "",
        )
        cm.add_qa_pair(request.conversation_id, request.question, answer)
        citation_data = _docs_to_citations(docs)

        return FollowUpResponse(
            question=request.question,
            answer=answer,
            context=vector_context,
            citations=citation_data,
            technical_terms=[],
            pipeline=_build_pipeline(pipeline_meta, citation_data),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Follow-up failed")
        raise _client_error("Follow-up failed. Please try again.")


@router.post("/followup/stream")
async def followup_stream(request: FollowUpRequest):
    """SSE follow-up: meta → token* → done."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    cm = get_conversation_manager()
    conversation = cm.store.get_conversation(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    def event_gen():
        try:
            conv_context = cm.get_conversation_context(request.conversation_id)
            original_query = (
                conversation.messages[0].content if conversation.messages else ""
            )
            docs, pipeline_meta = get_retriever().retrieve_with_meta(
                request.question, k=request.k
            )
            vector_context = format_context(docs)
            full_context = f"{conv_context}\n\nRELEVANT DOCUMENTS:\n{vector_context}"
            citation_data = _docs_to_citations(docs)
            pipeline = _build_pipeline(pipeline_meta, citation_data)

            yield _sse(
                "meta",
                {
                    "conversation_id": request.conversation_id,
                    "citations": citation_data,
                    "pipeline": pipeline,
                    "question": request.question,
                },
            )

            answer = None
            for kind, payload in get_qa_chain().answer_stream(
                request.question,
                original_query,
                full_context,
                "",
            ):
                if kind == "token":
                    yield _sse("token", {"text": payload})
                elif kind == "result":
                    answer = payload

            if answer is None:
                yield _sse("error", {"detail": "Empty answer"})
                return

            cm.add_qa_pair(request.conversation_id, request.question, answer)
            yield _sse(
                "done",
                {
                    "answer": answer,
                    "conversation_id": request.conversation_id,
                    "citations": citation_data,
                    "pipeline": pipeline,
                    "context": vector_context,
                },
            )
        except Exception:
            logger.exception("Follow-up stream failed")
            yield _sse("error", {"detail": "Follow-up failed. Please try again."})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations() -> ConversationListResponse:
    try:
        conversations = get_conversation_manager().store.list_conversations(limit=50)
        return {"conversations": conversations}
    except Exception:
        logger.exception("List conversations failed")
        raise _client_error("Failed to list conversations.")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = get_conversation_manager().store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conversation.id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata,
            }
            for msg in conversation.messages
        ],
        "metadata": conversation.metadata,
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    deleted = get_conversation_manager().store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "conversation_id": conversation_id}


def _pdf_source_id(document_id: str) -> str:
    return f"upload:{document_id}"


def _index_uploaded_pdf(processed, document_id: str) -> int:
    """Embed PDF chunks into an ephemeral in-memory index (not PubMed FAISS)."""
    docs = getattr(processed, "documents", None) or []
    docs = docs[:150]
    try:
        return get_retriever().index_upload(document_id, docs)
    except Exception:
        logger.exception("Failed to index uploaded PDF %s", document_id)
        return 0


def _index_documents(documents, document_id: str) -> int:
    try:
        return get_retriever().index_upload(document_id, documents[:150])
    except Exception:
        logger.exception("Failed to index uploaded PDF %s", document_id)
        return 0


def _uploaded_pdf_citation(processed, filename: str, document_id: str, score: float = 1.0) -> dict:
    title = (
        processed.metadata.title
        if processed.metadata.title
        and processed.metadata.title.strip().lower()
        not in ("", "unknown", "untitled")
        else filename
    )
    authors = []
    if processed.metadata.author:
        authors = [a.strip() for a in processed.metadata.author.split(",") if a.strip()]
    snippet = (processed.full_text[:280] + "...") if processed.full_text else None
    from urllib.parse import quote

    return {
        "id": _pdf_source_id(document_id),
        "title": title,
        "authors": authors,
        "authors_display": processed.metadata.author or "Uploaded PDF",
        "year": None,
        "journal": None,
        "formatted_citation": f"{processed.metadata.author or 'Uploaded PDF'}. {title}.",
        "apa_citation": f"{processed.metadata.author or 'Uploaded PDF'}. {title}.",
        "pmid": None,
        "arxiv_id": None,
        "doi": None,
        "urls": {
            "pubmed": None,
            "arxiv": None,
            "doi": None,
            "pdf": None,
            "main": None,
            "scholar": f"https://scholar.google.com/scholar?q={quote(title)}",
        },
        "relevance_score": score,
        "contribution_percentage": 0.0,
        "contribution": 0.0,
        "snippet": snippet,
        "abstract_preview": (processed.full_text[:200] + "...") if processed.full_text else None,
    }


def get_document_store():
    from core.document_store import get_document_store as _get
    return _get()


def _ingest_pdf_fast(contents: bytes, filename: str):
    """
    Fast path: extract text + chunks, store session, return manifest immediately.
    Tables/figures/FAISS run in background via _enrich_and_index_background.
    """
    import uuid

    document_id = str(uuid.uuid4())
    processed = get_pdf_processor().process_text_fast(
        contents, filename, document_id=document_id
    )
    enriched = processed.enrichment
    if enriched is None:
        raise RuntimeError("PDF enrichment missing from process_text_fast")

    metadata = {
        "title": processed.metadata.title,
        "author": processed.metadata.author,
        "pages": processed.metadata.num_pages,
    }
    store = get_document_store()
    stored = store.create(
        filename=filename,
        pdf_bytes=contents,
        num_pages=processed.metadata.num_pages,
        metadata=metadata,
        tables=[],
        figures=[],
        quality=enriched.quality,
        page_texts=enriched.page_texts,
        chunks=processed.chunks,
        full_text=processed.full_text,
        document_id=document_id,
    )
    manifest = store.to_manifest(stored)
    manifest["indexed_chunks"] = 0
    return stored, processed, manifest


def _enrich_and_index_background(document_id: str) -> None:
    """Detect tables/figures and index FAISS without blocking the reader."""
    from core.pdf_enrichment import enrich_pdf

    store = get_document_store()
    doc = store.get(document_id)
    if not doc:
        return

    quality = dict(doc.quality or {})
    quality["enrichment_status"] = "enriching"
    quality["index_status"] = "pending"
    store.update_quality(document_id, quality)

    try:
        pdf_bytes = store.read_pdf_bytes(document_id)
        if not pdf_bytes:
            quality["enrichment_status"] = "error"
            store.update_quality(document_id, quality)
            return

        enriched = enrich_pdf(pdf_bytes)
        quality = {
            **enriched.quality,
            "enrichment_status": "ready",
            "index_status": "indexing",
            "scanned_risk": enriched.quality.get(
                "scanned_risk", quality.get("scanned_risk", False)
            ),
            "avg_chars_per_page": enriched.quality.get(
                "avg_chars_per_page", quality.get("avg_chars_per_page", 0)
            ),
        }
        store.update_enrichment(
            document_id,
            tables=enriched.tables,
            figures=enriched.figures,
            quality=quality,
        )

        processor = get_pdf_processor()
        documents = processor.documents_from_stored(
            chunks=doc.chunks,
            source_name=doc.filename,
            document_id=document_id,
            title=(doc.metadata or {}).get("title"),
            author=(doc.metadata or {}).get("author"),
        )
        indexed = _index_documents(documents, document_id)
        quality = dict(store.get(document_id).quality or {})
        quality["index_status"] = "ready"
        quality["indexed_chunks"] = indexed
        quality["enrichment_status"] = "ready"
        store.update_quality(document_id, quality)
        logger.info(
            "Background enrichment done for %s: %s tables, %s figures, %s indexed",
            document_id,
            len(enriched.tables),
            len(enriched.figures),
            indexed,
        )
    except Exception:
        logger.exception("Background enrichment failed for %s", document_id)
        try:
            doc2 = store.get(document_id)
            if doc2:
                q = dict(doc2.quality or {})
                q["enrichment_status"] = "error"
                q["index_status"] = "error"
                store.update_quality(document_id, q)
        except Exception:
            pass


def _ingest_pdf_upload(contents: bytes, filename: str):
    """Legacy sync ingest (tests / fallback): full enrich + index before return."""
    import uuid

    document_id = str(uuid.uuid4())
    processed = get_pdf_processor().process_and_enrich(
        contents, filename, document_id=document_id
    )
    enriched = processed.enrichment
    if enriched is None:
        raise RuntimeError("PDF enrichment missing from process_and_enrich")

    quality = dict(enriched.quality)
    quality["enrichment_status"] = "ready"
    quality["index_status"] = "ready"

    metadata = {
        "title": processed.metadata.title,
        "author": processed.metadata.author,
        "pages": processed.metadata.num_pages,
    }
    store = get_document_store()
    stored = store.create(
        filename=filename,
        pdf_bytes=contents,
        num_pages=processed.metadata.num_pages,
        metadata=metadata,
        tables=enriched.tables,
        figures=enriched.figures,
        quality=quality,
        page_texts=enriched.page_texts,
        chunks=processed.chunks,
        full_text=processed.full_text,
        document_id=document_id,
    )
    indexed = _index_uploaded_pdf(processed, document_id)
    quality["indexed_chunks"] = indexed
    store.update_quality(document_id, quality)
    stored = store.get(document_id) or stored
    manifest = store.to_manifest(stored)
    manifest["indexed_chunks"] = indexed
    return stored, processed, indexed, manifest


class AnalyzeRequest(BaseModel):
    content_type: str = Field(..., description="text | table | figure")
    action: str = Field(default="summarize")
    conversation_id: Optional[str] = None
    text: Optional[str] = None
    page: Optional[int] = None
    table_id: Optional[str] = None
    figure_id: Optional[str] = None
    question: Optional[str] = None


class SimplifyDocumentRequest(BaseModel):
    conversation_id: Optional[str] = None


@router.post("/upload/pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        contents = await file.read()
        if not _validate_pdf(contents):
            raise HTTPException(status_code=400, detail="Invalid PDF file")
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        _stored, _processed, manifest = _ingest_pdf_fast(contents, file.filename)
        background_tasks.add_task(_enrich_and_index_background, _stored.id)
        return manifest
    except HTTPException:
        raise
    except Exception:
        logger.exception("PDF upload failed")
        raise _client_error("Error processing PDF.")


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    store = get_document_store()
    doc = store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or expired")
    return store.to_manifest(doc)


@router.get("/documents/{document_id}/pages/{page}")
async def get_document_page(document_id: str, page: int):
    store = get_document_store()
    text = store.get_page_text(document_id, page)
    if text is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"page": page, "text": text}


@router.get("/documents/{document_id}/tables/{table_id}")
async def get_document_table(document_id: str, table_id: str):
    store = get_document_store()
    table = store.get_table(document_id, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return {
        "id": table["id"],
        "page": table["page"],
        "bbox": table["bbox"],
        "caption": table.get("caption"),
        "confidence": table.get("confidence", 0.5),
        "markdown": table.get("markdown") or "",
        "rows": table.get("rows"),
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        get_retriever().drop_upload(document_id)
    except Exception:
        logger.debug("Upload index drop skipped for %s", document_id)
    deleted = get_document_store().delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "document_id": document_id}


def _simplify_stored_document(document_id: str, conversation_id: Optional[str] = None):
    store = get_document_store()
    doc = store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or expired")

    # Prefer stored chunks — avoid re-parsing the PDF
    processor = get_pdf_processor()
    if doc.chunks:
        documents = processor.documents_from_stored(
            chunks=doc.chunks,
            source_name=doc.filename,
            document_id=document_id,
            title=doc.metadata.get("title"),
            author=doc.metadata.get("author"),
        )
        full_text = doc.full_text or "\n\n".join(doc.chunks)
        title = doc.metadata.get("title")
        author = doc.metadata.get("author")
        num_pages = doc.num_pages
        indexed = _index_documents(documents, document_id)
    else:
        pdf_bytes = store.read_pdf_bytes(document_id)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file missing")
        processed = processor.process_and_enrich(
            pdf_bytes, doc.filename, document_id=document_id
        )
        documents = processed.documents
        full_text = processed.full_text
        title = processed.metadata.title
        author = processed.metadata.author
        num_pages = processed.metadata.num_pages
        indexed = _index_uploaded_pdf(processed, document_id)

    query = full_text[:4000]
    own_docs = [
        (d, 1.0 / (1.0 + i)) for i, d in enumerate(documents[:8])
    ]
    search_hint = title or query[:400]
    related, pipeline_meta = get_retriever().retrieve_with_meta(search_hint, k=3)
    own_source = _pdf_source_id(document_id)
    related = [
        (d, score)
        for d, score in related
        if (d.metadata or {}).get("source") != own_source
    ]

    vector_context = format_context(own_docs + related)
    simplify_result = get_simplifier().simplify(query, vector_context)

    # Build a lightweight processed-like object for citation helper
    class _Meta:
        pass

    meta = _Meta()
    meta.title = title
    meta.author = author
    meta.num_pages = num_pages

    class _Processed:
        pass

    processed_like = _Processed()
    processed_like.metadata = meta
    processed_like.full_text = full_text

    uploaded = _uploaded_pdf_citation(
        processed_like, doc.filename, document_id, score=1.0
    )
    related_cites = _docs_to_citations(related)
    corpus = related_cites.get("sources") or []
    if corpus:
        total = sum(
            float(s.get("contribution") or s.get("contribution_percentage") or 0)
            for s in corpus
        ) or len(corpus)
        for s in corpus:
            raw = float(
                s.get("contribution") or s.get("contribution_percentage") or 0
            ) or (100 / len(corpus))
            pct = round((raw / total) * 40.0, 1)
            s["contribution"] = pct
            s["contribution_percentage"] = pct
        uploaded["contribution"] = 60.0
        uploaded["contribution_percentage"] = 60.0
    else:
        uploaded["contribution"] = 100.0
        uploaded["contribution_percentage"] = 100.0

    citation_data = {
        "sources": [uploaded, *corpus],
        "total": 1 + len(corpus),
        "primary_source": uploaded,
    }
    pipeline = _build_pipeline(
        {**(pipeline_meta or {}), "indexed_chunks": indexed, "document_id": document_id},
        citation_data,
    )

    cm = get_conversation_manager()
    if conversation_id:
        cm.store.add_message(
            conversation_id,
            "user",
            f"Simplify entire PDF: {doc.filename}",
            {"type": "pdf_simplify", "document_id": document_id},
        )
        conv_id = conversation_id
    else:
        conv_id = cm.start_conversation(
            f"PDF: {doc.filename}",
            {
                "type": "pdf_upload",
                "filename": doc.filename,
                "document_id": document_id,
                "indexed_chunks": indexed,
            },
        )
    cm.add_assistant_response(
        conv_id, simplify_result.text, _docs_to_results(own_docs + related)
    )

    return {
        "document_id": document_id,
        "filename": doc.filename,
        "metadata": {
            "title": title,
            "author": author,
            "pages": num_pages,
        },
        "indexed_chunks": indexed,
        "simplified_text": simplify_result.text,
        "context": vector_context,
        "citations": citation_data,
        "technical_terms": simplify_result.technical_terms,
        "conversation_id": conv_id,
        "pipeline": pipeline,
    }


@router.post("/documents/{document_id}/simplify")
async def simplify_document(
    document_id: str,
    request: SimplifyDocumentRequest = SimplifyDocumentRequest(),
):
    try:
        return _simplify_stored_document(document_id, request.conversation_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Document simplify failed")
        raise _client_error("Error simplifying PDF.")


@router.post("/documents/{document_id}/analyze/stream")
async def analyze_document_stream(document_id: str, request: AnalyzeRequest):
    """SSE: meta → token* → terms? → done for text/table selection."""
    if request.content_type == "figure":
        raise HTTPException(
            status_code=400,
            detail="Use /documents/{id}/analyze/vision/stream for figures",
        )
    if request.content_type not in ("text", "table"):
        raise HTTPException(status_code=400, detail="content_type must be text or table")

    def event_gen():
        from core.selection_analyzer import AnalyzeResultBag, analyze_stream

        try:
            store = get_document_store()
            doc = store.get(document_id)
            if not doc:
                yield _sse("error", {"detail": "Document not found or expired"})
                return

            source_ref = {
                "content_type": request.content_type,
                "page": request.page,
                "action": request.action,
            }
            label = "Selected text"
            warnings: list[str] = []

            if request.content_type == "table":
                table = store.get_table(document_id, request.table_id or "")
                if not table:
                    yield _sse("error", {"detail": "Table not found"})
                    return
                source_ref["id"] = table["id"]
                source_ref["page"] = table.get("page")
                label = table.get("caption") or f"Table on page {table.get('page')}"
                if (table.get("confidence") or 0) < 0.5:
                    warnings.append(
                        "Table structure may be imperfect — results could be inaccurate."
                    )
            else:
                source_ref["id"] = None
                label = f"Page {request.page} selection" if request.page else "Selected text"

            cm = get_conversation_manager()
            user_msg = f"[{request.action}] {label}"
            if request.content_type == "text" and request.text:
                if request.action == "ask" and request.question:
                    user_msg = f"[ask] {request.question}"
                else:
                    user_msg = f"[{request.action}] {request.text[:200]}"

            if request.conversation_id:
                conversation_id = request.conversation_id
                cm.store.add_message(
                    conversation_id,
                    "user",
                    user_msg,
                    {
                        "type": "pdf_analyze",
                        "document_id": document_id,
                        "source_ref": source_ref,
                        "action": request.action,
                    },
                )
            else:
                conversation_id = cm.start_conversation(
                    user_msg,
                    {
                        "type": "pdf_analyze",
                        "document_id": document_id,
                        "filename": doc.filename,
                        "title": f"PDF: {doc.metadata.get('title') or doc.filename}",
                    },
                )

            yield _sse(
                "meta",
                {
                    "conversation_id": conversation_id,
                    "content_type": request.content_type,
                    "source_ref": {**source_ref, "label": label},
                    "action": request.action,
                    "warnings": warnings,
                },
            )

            bag = AnalyzeResultBag()
            for token in analyze_stream(
                store,
                document_id,
                content_type=request.content_type,
                action=request.action,
                text=request.text,
                page=request.page,
                table_id=request.table_id,
                question=request.question,
                result_bag=bag,
            ):
                yield _sse("token", {"text": token})

            body = bag.text
            terms = bag.terms or []
            if terms:
                yield _sse("terms", {"technical_terms": terms})

            cm.add_assistant_response(conversation_id, body or "", None)
            yield _sse(
                "done",
                {
                    "text": body,
                    "simplified_text": body,
                    "technical_terms": terms,
                    "conversation_id": conversation_id,
                },
            )
        except Exception as e:
            logger.exception("Analyze stream failed")
            yield _sse("error", {"detail": str(e) or "Analysis failed"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/documents/{document_id}/analyze/vision/stream")
async def analyze_figure_vision_stream(document_id: str, request: AnalyzeRequest):
    """SSE vision analysis for figure regions."""
    if request.content_type != "figure":
        raise HTTPException(status_code=400, detail="content_type must be figure")
    if not request.figure_id:
        raise HTTPException(status_code=400, detail="figure_id is required")

    def event_gen():
        from core.vision_analyzer import analyze_figure_stream

        try:
            store = get_document_store()
            doc = store.get(document_id)
            if not doc:
                yield _sse("error", {"detail": "Document not found or expired"})
                return

            figure = store.get_figure(document_id, request.figure_id)
            if not figure:
                yield _sse("error", {"detail": "Figure not found"})
                return

            label = figure.get("caption") or f"Figure on page {figure.get('page')}"
            source_ref = {
                "content_type": "figure",
                "id": figure["id"],
                "page": figure.get("page"),
                "label": label,
                "action": request.action or "explain",
            }

            cm = get_conversation_manager()
            user_msg = f"[{request.action or 'explain'}] {label}"
            if request.conversation_id:
                conversation_id = request.conversation_id
                cm.store.add_message(
                    conversation_id,
                    "user",
                    user_msg,
                    {
                        "type": "pdf_analyze",
                        "document_id": document_id,
                        "source_ref": source_ref,
                    },
                )
            else:
                conversation_id = cm.start_conversation(
                    user_msg,
                    {
                        "type": "pdf_analyze",
                        "document_id": document_id,
                        "filename": doc.filename,
                        "title": f"PDF: {doc.metadata.get('title') or doc.filename}",
                    },
                )

            yield _sse(
                "meta",
                {
                    "conversation_id": conversation_id,
                    "content_type": "figure",
                    "source_ref": source_ref,
                    "action": request.action or "explain",
                    "warnings": [],
                },
            )

            collected: list[str] = []
            used_vision = False
            settings = get_settings()
            provider = (settings.llm_provider or "google").strip().lower()
            vision_ok = provider == "google"
            if not vision_ok:
                yield _sse(
                    "meta",
                    {
                        "conversation_id": conversation_id,
                        "content_type": "figure",
                        "source_ref": source_ref,
                        "action": request.action or "explain",
                        "warnings": [
                            "Caption-only — figure vision needs Gemini (llm_provider=google)."
                        ],
                        "used_vision": False,
                        "vision_available": False,
                    },
                )

            for token, vision in analyze_figure_stream(
                store,
                document_id,
                figure_id=request.figure_id,
                action=request.action or "explain",
            ):
                used_vision = used_vision or vision
                collected.append(token)
                yield _sse("token", {"text": token})

            full = "".join(collected)
            if not used_vision and vision_ok:
                yield _sse(
                    "meta",
                    {
                        "conversation_id": conversation_id,
                        "content_type": "figure",
                        "source_ref": source_ref,
                        "action": request.action or "explain",
                        "warnings": [
                            "Caption-only analysis (could not read the figure image)."
                        ],
                        "used_vision": False,
                    },
                )

            cm.add_assistant_response(conversation_id, full, None)
            yield _sse(
                "done",
                {
                    "text": full,
                    "simplified_text": full,
                    "technical_terms": [],
                    "conversation_id": conversation_id,
                    "used_vision": used_vision,
                },
            )
        except Exception as e:
            logger.exception("Vision analyze failed")
            yield _sse("error", {"detail": str(e) or "Vision analysis failed"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/upload/pdf-simplify")
async def upload_and_simplify(file: UploadFile = File(...)):
    """Backward-compatible: upload + simplify. Prefer /documents/{id}/simplify. """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        contents = await file.read()
        if not _validate_pdf(contents):
            raise HTTPException(status_code=400, detail="Invalid PDF file")
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        stored, _processed, _indexed, _manifest = _ingest_pdf_upload(
            contents, file.filename
        )
        return _simplify_stored_document(stored.id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("PDF simplify failed")
        raise _client_error("Error processing PDF.")


@router.get("/health")
async def health() -> dict:
    """Health check with vector store and Gemini model status."""
    status = {"status": "healthy", "version": "2.0.0", "checks": {}}

    try:
        get_retriever()
        status["checks"]["vector_store"] = "ok"
    except Exception as e:
        status["checks"]["vector_store"] = f"error: {e}"
        status["status"] = "degraded"

    try:
        resolve_model()
        status["checks"]["llm_provider"] = get_settings().llm_provider
        status["checks"]["llm_model"] = get_resolved_model_name()
    except Exception as e:
        status["checks"]["llm_model"] = f"error: {e}"
        status["status"] = "degraded"

    settings = get_settings()
    status["checks"]["embedding_model"] = settings.embedding_model
    status["checks"]["normalize_embeddings"] = settings.normalize_embeddings
    provider = (settings.llm_provider or "google").strip().lower()
    status["checks"]["vision_available"] = provider == "google"
    return status

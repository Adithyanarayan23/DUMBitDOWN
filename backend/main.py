"""Main FastAPI application entry point."""
import asyncio
import logging

import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import get_settings

logger = logging.getLogger(__name__)

# Configure Gemini API once at startup (only when using the Google provider)
settings = get_settings()
_api_key = (settings.google_api_key or "").strip()
if (
    (settings.llm_provider or "google").strip().lower() == "google"
    and _api_key
    and not _api_key.startswith("your_")
):
    genai.configure(api_key=_api_key)

# Create FastAPI app
app = FastAPI(
    title="DumbItDown API",
    description="Research text simplification and Q&A",
    version="2.0.0"
)

_cors_origins = [
    o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()
]
if not _cors_origins:
    _cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
# Wildcard + credentials is invalid/unsafe — drop credentials if someone sets *
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")

_ttl_task: asyncio.Task | None = None


async def _document_ttl_loop():
    """Periodically purge expired uploaded documents."""
    from core.document_store import get_document_store

    while True:
        try:
            removed = get_document_store().cleanup_expired()
            if removed:
                logger.info("TTL cleanup removed %s documents", removed)
        except Exception:
            logger.exception("Document TTL cleanup failed")
        await asyncio.sleep(3600)


@app.on_event("startup")
async def _on_startup():
    global _ttl_task
    from core.document_store import get_document_store

    try:
        removed = get_document_store().cleanup_expired()
        logger.info("Startup TTL cleanup removed %s documents", removed)
    except Exception:
        logger.exception("Startup document cleanup failed")
    _ttl_task = asyncio.create_task(_document_ttl_loop())


@app.on_event("shutdown")
async def _on_shutdown():
    global _ttl_task
    if _ttl_task:
        _ttl_task.cancel()
        try:
            await _ttl_task
        except asyncio.CancelledError:
            pass
        _ttl_task = None


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "DumbItDown API",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )

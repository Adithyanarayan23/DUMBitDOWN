"""Application configuration using pydantic-settings."""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM provider: "google" (Gemini) or "groq"
    llm_provider: str = Field(default="google", description="google or groq")

    # API Keys
    google_api_key: str | None = Field(None, description="Google Gemini API key")
    groq_api_key: str | None = Field(None, description="Groq API key")
    hf_api_key: str | None = Field(None, description="HuggingFace API key (optional)")

    # Server Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 5000

    # Comma-separated browser origins allowed to call the API (no wildcard in prod)
    cors_origins: str = Field(
        default=(
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:3001,http://127.0.0.1:3001"
        ),
        description="Allowed CORS origins",
    )

    # Deployment Mode (local = FAISS file-based, cloud = Qdrant hosted)
    deployment: str = Field(default="local", description="local or cloud")

    # FAISS settings (used when deployment=local)
    vector_store_path: Path = Field(default=Path("vector_store"))

    # Qdrant settings (used when deployment=cloud)
    qdrant_url: str | None = Field(None, description="Qdrant cloud URL")
    qdrant_api_key: str | None = Field(None, description="Qdrant API key")
    qdrant_collection: str = Field(default="dumbitdown_papers", description="Collection name")

    @property
    def vector_store_type(self) -> str:
        """Map deployment mode to vector store type."""
        return "qdrant" if self.deployment == "cloud" else "faiss"

    # Embedding Model — must match how the existing FAISS index was built
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    normalize_embeddings: bool = False

    # RAG Configuration
    top_k: int = 5
    rerank_top_n: int = 3

    # LLM Configuration
    temperature: float = 0.1
    max_output_tokens: int = 1024
    gemini_model: str = "models/gemini-2.0-flash"
    gemini_fallback_models: str = (
        "gemini-2.0-flash,gemini-2.0-flash-lite,gemini-flash-latest"
    )

    # Groq settings (used when llm_provider=groq)
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fallback_models: str = "llama-3.3-70b-versatile,llama-3.1-8b-instant,openai/gpt-oss-20b"

    # Conversation Database
    conversation_db_path: str = Field(default="conversations.db")

    # Uploaded document sessions (interactive PDF reader)
    documents_db_path: str = Field(default="documents.db")
    uploads_dir: Path = Field(default=Path("uploads"))
    document_ttl_hours: int = Field(default=24)
    max_inline_pages: int = Field(default=25)
    max_table_preview_chars: int = Field(default=200)
    figure_render_scale: float = Field(default=2.0)

    class Config:
        env_file = (
            str(_BACKEND_DIR / ".env"),
            str(_ROOT_DIR / ".env"),
        )
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

import os
from typing import Literal, Self

from loguru import logger
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = "development"

    # LLM Settings
    LLM_PROVIDER: Literal["openai", "groq", "ollama", "gemini"] = "openai"

    # OpenAI Settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Groq Settings
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Gemini Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Search API
    TAVILY_API_KEY: str = ""

    # Vector Database Settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "multi_agent_rag"

    # RAG Retrieval & Grading Settings
    DOCUMENT_RELEVANCE_THRESHOLD: float = 0.7
    MAX_RETRIES: int = 3
    RETRIEVAL_TOP_K: int = 4
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150
    HYBRID_SEARCH_ENABLED: bool = True
    RERANKING_ENABLED: bool = False
    REQUEST_TIMEOUT_SECONDS: float = 30.0

    # API Security & Server Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ALLOWED_INGESTION_DIR: str = ""
    UPLOAD_DIR: str = ""
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_QUESTION_LENGTH: int = 2000
    API_KEY_AUTH_ENABLED: bool = False
    API_KEY: str = ""
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1|.*\.vercel\.app)(:\d+)?$"

    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("GEMINI_MODEL", mode="before")
    @classmethod
    def sanitize_gemini_model(cls, v: object) -> str:
        """Ensures a valid Google Gemini model identifier is configured."""
        if isinstance(v, str):
            model = v.strip()
            if "3.5" in model or "3.6" in model or not model:
                return "gemini-1.5-flash"
            return model
        return "gemini-1.5-flash"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        """Parses comma-separated string or list into a list of allowed origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]

    def _resolve_paths(self) -> None:
        """Resolves canonical directory paths for ingestion, uploads, and Chroma."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.BASE_DIR = project_root

        if not self.ALLOWED_INGESTION_DIR:
            self.ALLOWED_INGESTION_DIR = os.path.abspath(
                os.path.join(project_root, "sample_documents")
            )
        elif not os.path.isabs(self.ALLOWED_INGESTION_DIR):
            self.ALLOWED_INGESTION_DIR = os.path.abspath(
                os.path.join(project_root, self.ALLOWED_INGESTION_DIR)
            )

        if not self.UPLOAD_DIR:
            self.UPLOAD_DIR = os.path.abspath(os.path.join(project_root, "uploaded_documents"))
        elif not os.path.isabs(self.UPLOAD_DIR):
            self.UPLOAD_DIR = os.path.abspath(os.path.join(project_root, self.UPLOAD_DIR))

        db_path = self.CHROMA_PERSIST_DIRECTORY
        if not os.path.isabs(db_path):
            self.CHROMA_PERSIST_DIRECTORY = os.path.abspath(os.path.join(project_root, db_path))

    def _validate_credentials(self) -> None:
        """Validates API credentials according to the current environment."""
        provider = self.LLM_PROVIDER.lower()
        is_production = self.ENVIRONMENT.lower() == "production"

        key_map = {
            "openai": (self.OPENAI_API_KEY, "your-openai-api-key"),
            "groq": (self.GROQ_API_KEY, "your-groq-api-key"),
            "gemini": (self.GEMINI_API_KEY, "your-gemini-api-key"),
        }

        if provider in key_map:
            key, placeholder = key_map[provider]
            if not key or placeholder in key:
                if is_production:
                    raise ValueError(f"{provider.upper()}_API_KEY is required in production mode.")
                logger.warning(
                    f"{provider.upper()}_API_KEY is not configured. Requests requiring {provider.title()} LLM will fail."
                )

        if not self.TAVILY_API_KEY or "your-tavily-api-key" in self.TAVILY_API_KEY:
            logger.info("TAVILY_API_KEY is not set. Web search fallback will be disabled.")

    @model_validator(mode="after")
    def validate_and_resolve(self) -> Self:
        """Validates credentials and resolves canonical directory paths."""
        self._resolve_paths()
        self._validate_credentials()
        return self


# Instantiate the global settings object
settings = Settings()

import os
from typing import Literal, Self

from loguru import logger
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # LLM Settings
    LLM_PROVIDER: Literal["openai", "groq", "ollama", "gemini"] = "openai"

    # OpenAI Settings
    OPENAI_API_KEY: str = "mock-openai-key"
    OPENAI_MODEL: str = "gpt-4o"

    # Groq Settings
    GROQ_API_KEY: str = "mock-groq-key"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Gemini Settings
    GEMINI_API_KEY: str = "mock-gemini-key"
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Search API
    TAVILY_API_KEY: str = "mock-tavily-key"

    # Vector Database Settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "multi_agent_rag"

    # RAG Grading Settings
    DOCUMENT_RELEVANCE_THRESHOLD: float = 0.7
    MAX_RETRIES: int = 3

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_api_keys(self) -> Self:
        """Logs warnings if active provider API keys are missing or use default mocks."""
        provider = self.LLM_PROVIDER.lower()

        if provider == "openai":
            if (
                not self.OPENAI_API_KEY
                or "your-openai-api-key" in self.OPENAI_API_KEY
                or self.OPENAI_API_KEY == "mock-openai-key"
            ):
                logger.warning(
                    "OPENAI_API_KEY is not set or using a default mock value. API requests will fail."
                )
        elif provider == "groq":
            if (
                not self.GROQ_API_KEY
                or "your-groq-api-key" in self.GROQ_API_KEY
                or self.GROQ_API_KEY == "mock-groq-key"
            ):
                logger.warning(
                    "GROQ_API_KEY is not set or using a default mock value. API requests will fail."
                )
        elif provider == "gemini":
            if (
                not self.GEMINI_API_KEY
                or "your-gemini-api-key" in self.GEMINI_API_KEY
                or self.GEMINI_API_KEY == "mock-gemini-key"
            ):
                logger.warning(
                    "GEMINI_API_KEY is not set or using a default mock value. API requests will fail."
                )

        if (
            not self.TAVILY_API_KEY
            or "your-tavily-api-key" in self.TAVILY_API_KEY
            or self.TAVILY_API_KEY == "mock-tavily-key"
        ):
            logger.warning(
                "TAVILY_API_KEY is not set or using a default mock value. Web searches will fail."
            )

        # Resolve relative DB directory path to absolute path relative to config file folder
        db_path = self.CHROMA_PERSIST_DIRECTORY
        if not os.path.isabs(db_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.CHROMA_PERSIST_DIRECTORY = os.path.abspath(os.path.join(project_root, db_path))

        return self


# Instantiate the global settings object
settings = Settings()

from unittest.mock import patch

from app.llm.gemini import get_gemini_llm
from app.llm.provider import get_llm


def test_get_gemini_llm() -> None:
    """Verifies get_gemini_llm instantiates LLM without errors."""
    with patch("app.config.settings.GEMINI_API_KEY", "test-gemini-key"):
        with patch("app.config.settings.GEMINI_MODEL", "gemini-3.6-flash"):
            llm = get_gemini_llm(temperature=0.0)
            assert llm is not None


def test_provider_factory_gemini() -> None:
    """Verifies get_llm factory delegates to get_gemini_llm when LLM_PROVIDER=gemini."""
    with patch("app.config.settings.LLM_PROVIDER", "gemini"):
        with patch("app.config.settings.GEMINI_API_KEY", "test-gemini-key"):
            llm = get_llm(temperature=0.2)
            assert llm is not None

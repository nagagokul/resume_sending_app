from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.ollama import OllamaProvider
from app.llm.providers import GeminiProvider, OpenAICompatibleProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return GeminiProvider()
    if settings.llm_provider == "openai":
        return OpenAICompatibleProvider()
    return OllamaProvider()

from __future__ import annotations

import json
import re
from typing import TypeVar

import httpx
import structlog
from pydantic import BaseModel

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.ollama import _extract_json, _hash_embed

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider(LLMProvider):
    """Optional OpenAI-compatible provider (OpenAI, Groq, Together, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._base_url = (base_url or settings.openai_base_url).rstrip("/")
        self._model = model or settings.openai_model
        self._embed_model = embed_model or settings.openai_embed_model

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise RuntimeError("OpenAI API key not configured")
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def structured_generate(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            (system or "")
            + "\nReturn ONLY valid JSON matching this schema. Do not invent facts.\n"
            + schema_json
        ).strip()
        raw = await self.generate(prompt, system=full_system, temperature=temperature)
        return schema.model_validate(_extract_json(raw))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            return [_hash_embed(t) for t in texts]
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers=self._headers(),
                json={"model": self._embed_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


class GeminiProvider(LLMProvider):
    """Optional Google Gemini provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.gemini_api_key
        self._model = model or settings.gemini_model

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        if not self._api_key:
            raise RuntimeError("Gemini API key not configured")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        parts = []
        if system:
            parts.append({"text": f"System: {system}\n\nUser: {prompt}"})
        else:
            parts.append({"text": prompt})
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
                },
            )
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if not candidates:
                return ""
            return candidates[0]["content"]["parts"][0].get("text", "")

    async def structured_generate(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            (system or "")
            + "\nReturn ONLY valid JSON matching this schema. Do not invent facts.\n"
            + schema_json
        ).strip()
        raw = await self.generate(prompt, system=full_system, temperature=temperature)
        return schema.model_validate(_extract_json(raw))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Gemini embedding via paid API; fall back to hash embed for free-first mode
        return [_hash_embed(t) for t in texts]

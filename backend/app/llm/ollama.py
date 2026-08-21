from __future__ import annotations

import json
import re
from typing import TypeVar

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.llm.base import LLMProvider

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._embed_model = embed_model or settings.ollama_embed_model

    @property
    def name(self) -> str:
        return "ollama"

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
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except httpx.HTTPError as exc:
            logger.warning("ollama_generate_failed", error=str(exc))
            raise RuntimeError(f"Ollama generate failed: {exc}") from exc

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
            + "\n\nReturn ONLY valid JSON matching this schema. Do not invent facts.\n"
            + schema_json
        ).strip()
        raw = await self.generate(prompt, system=full_system, temperature=temperature)
        data = _extract_json(raw)
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            logger.warning("ollama_structured_validation_failed", error=str(exc), raw=raw[:500])
            raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for text in texts:
                    resp = await client.post(
                        f"{self._base_url}/api/embeddings",
                        json={"model": self._embed_model, "prompt": text},
                    )
                    resp.raise_for_status()
                    vectors.append(resp.json()["embedding"])
            return vectors
        except httpx.HTTPError as exc:
            logger.warning("ollama_embed_failed", error=str(exc))
            # Fallback: deterministic pseudo-embedding for offline/dev without Ollama
            return [_hash_embed(t, dim=768) for t in texts]


def _extract_json(text: str) -> dict | list:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return json.loads(fence.group(1).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("No JSON object found in model response")


def _hash_embed(text: str, dim: int = 768) -> list[float]:
    """Deterministic bag-of-tokens fallback when Ollama embeddings unavailable."""
    import hashlib
    import math

    vec = [0.0] * dim
    tokens = re.findall(r"[a-z0-9+#]+", text.lower())
    if not tokens:
        return vec
    for tok in tokens:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]

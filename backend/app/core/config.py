from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(REPO_ROOT / ".env"),
            str(BACKEND_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Job Application Agent"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    log_level: str = "INFO"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_job_agent"
    # Alembic / sync engine — use psycopg3 driver (not psycopg2)
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_agent"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret: str = "change-me-in-production-use-long-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    llm_provider: Literal["ollama", "gemini", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"
    embedding_provider: Literal["ollama", "openai"] = "ollama"
    embedding_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    upload_dir: str = str(BACKEND_ROOT / "uploads")
    max_upload_size_mb: int = 10
    allowed_resume_extensions: str = ".pdf,.docx,.txt"

    # Default India + remote job discovery boards (public Greenhouse/Lever tokens)
    default_greenhouse_boards: str = (
        "stripe,airbnb,coinbase,datadog,hashicorp,cloudflare,mongodb,elastic,"
        "gitlab,notion,figma,asana,dropbox,nvidia,intel,qualcomm"
    )
    default_lever_companies: str = (
        "netflix,spotify,palantir,twitch,shopify,postman,ramp,brex"
    )

    rate_limit_per_minute: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_resume_extensions.split(",") if e.strip()}

    @property
    def greenhouse_boards(self) -> list[str]:
        return [b.strip() for b in self.default_greenhouse_boards.split(",") if b.strip()]

    @property
    def lever_companies(self) -> list[str]:
        return [c.strip() for c in self.default_lever_companies.split(",") if c.strip()]

    @property
    def resolved_embed_model(self) -> str:
        return self.embedding_model or self.ollama_embed_model


@lru_cache
def get_settings() -> Settings:
    return Settings()

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health() -> dict:
        checks = {
            "database": await _check_database(),
            "redis": await _check_redis(settings.redis_url),
            "ollama": await _check_ollama(settings.ollama_base_url),
        }
        overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
        return {"status": overall, "service": settings.app_name, **checks}

    return app


async def _check_database() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis(redis_url: str) -> str:
    try:
        import redis.asyncio as redis_async

        client = redis_async.from_url(redis_url, socket_connect_timeout=2)
        try:
            pong = await client.ping()
            return "ok" if pong else "error"
        finally:
            await client.aclose()
    except Exception:
        return "error"


async def _check_ollama(base_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return "ok" if resp.status_code < 500 else "error"
    except Exception:
        return "error"


app = create_app()

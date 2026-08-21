from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.jobs.ingestion import discover_jobs
from app.workers.celery_app import celery_app

logger = structlog.get_logger()
settings = get_settings()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(name="jobs.discover")
def discover_jobs_task(
    sources: list[str] | None = None,
    limit: int = 100,
) -> dict:
    async def _inner() -> dict:
        async with AsyncSessionLocal() as session:
            try:
                result = await discover_jobs(session, sources=sources, limit=limit)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    logger.info("celery_discover_jobs_start")
    return _run(_inner())


@celery_app.task(name="jobs.ping")
def ping() -> str:
    return "pong"

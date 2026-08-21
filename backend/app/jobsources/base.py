from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawJob:
    source: str
    source_job_id: str
    company: str
    title: str
    description: str | None = None
    location: str | None = None
    application_url: str | None = None
    employment_type: str | None = None
    posted_at: datetime | None = None
    updated_at: datetime | None = None
    salary: dict[str, Any] | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchJobsParams:
    query: str | None = None
    locations: list[str] | None = None
    remote_only: bool = False
    india_only: bool = False
    limit: int = 100
    board_tokens: list[str] | None = None  # Greenhouse
    company_tokens: list[str] | None = None  # Lever


class JobSource(ABC):
    """Modular job-source interface. Implementations must use public/official APIs only."""

    name: str
    display_name: str

    @abstractmethod
    async def fetch_jobs(self, params: FetchJobsParams) -> list[RawJob]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_job(self, source_job_id: str, **kwargs: Any) -> RawJob | None:
        raise NotImplementedError

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.jobsources.base import FetchJobsParams, JobSource, RawJob


class ManualJobSource(JobSource):
    """User-provided job URLs — stores metadata without scraping restricted sites."""

    name = "manual"
    display_name = "User Provided"

    async def fetch_jobs(self, params: FetchJobsParams) -> list[RawJob]:
        return []

    async def fetch_job(self, source_job_id: str, **kwargs: Any) -> RawJob | None:
        url = kwargs.get("url") or source_job_id
        title = kwargs.get("title") or "User-provided role"
        company = kwargs.get("company") or _guess_company(url)
        description = kwargs.get("description")
        location = kwargs.get("location")
        return RawJob(
            source=self.name,
            source_job_id=url,
            company=company,
            title=title,
            description=description,
            location=location,
            application_url=url,
            raw_payload={"url": url},
        )


def _guess_company(url: str) -> str:
    try:
        host = urlparse(url).netloc
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].title()
        return host or "Unknown"
    except Exception:
        return "Unknown"

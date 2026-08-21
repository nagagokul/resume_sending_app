from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

from app.jobsources.base import FetchJobsParams, JobSource, RawJob

logger = structlog.get_logger()

LEVER_API = "https://api.lever.co/v0/postings"


class LeverJobSource(JobSource):
    """Public Lever postings API — no auth required for public company sites."""

    name = "lever"
    display_name = "Lever"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch_jobs(self, params: FetchJobsParams) -> list[RawJob]:
        companies = params.company_tokens or []
        jobs: list[RawJob] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for company in companies:
                try:
                    company_jobs = await self._fetch_company(client, company, params)
                    jobs.extend(company_jobs)
                    if len(jobs) >= params.limit:
                        break
                except httpx.HTTPError as exc:
                    logger.warning("lever_company_failed", company=company, error=str(exc))
        return jobs[: params.limit]

    async def fetch_job(self, source_job_id: str, **kwargs: Any) -> RawJob | None:
        company = kwargs.get("company_token")
        if not company:
            return None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{LEVER_API}/{company}/{source_job_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._map_job(resp.json(), company)

    async def _fetch_company(
        self, client: httpx.AsyncClient, company: str, params: FetchJobsParams
    ) -> list[RawJob]:
        resp = await client.get(f"{LEVER_API}/{company}", params={"mode": "json"})
        if resp.status_code == 404:
            logger.info("lever_company_not_found", company=company)
            return []
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        results: list[RawJob] = []
        for item in data:
            raw = self._map_job(item, company)
            if self._matches_filters(raw, params):
                results.append(raw)
        return results

    def _map_job(self, item: dict[str, Any], company: str) -> RawJob:
        categories = item.get("categories") or {}
        location = categories.get("location") or item.get("location")
        if isinstance(location, dict):
            location = location.get("name")
        description_parts = []
        for key in ("descriptionPlain", "description", "additional"):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                description_parts.append(val)
            elif isinstance(val, dict) and val.get("text"):
                description_parts.append(val["text"])
        lists = item.get("lists") or []
        for lst in lists:
            if isinstance(lst, dict):
                description_parts.append(f"{lst.get('text', '')}\n{lst.get('content', '')}")
        posted = None
        if item.get("createdAt"):
            try:
                # Lever uses epoch ms
                ts = item["createdAt"]
                if isinstance(ts, (int, float)):
                    posted = datetime.utcfromtimestamp(ts / 1000.0)
            except (ValueError, OSError, TypeError):
                posted = None
        return RawJob(
            source=self.name,
            source_job_id=str(item.get("id") or item.get("id")),
            company=company.replace("-", " ").title(),
            title=item.get("text") or item.get("title") or "Untitled",
            description="\n\n".join(description_parts) or None,
            location=location if isinstance(location, str) else None,
            application_url=item.get("hostedUrl") or item.get("applyUrl"),
            employment_type=categories.get("commitment"),
            posted_at=posted,
            updated_at=posted,
            salary=None,
            raw_payload={"company_token": company, "id": item.get("id")},
        )

    def _matches_filters(self, job: RawJob, params: FetchJobsParams) -> bool:
        text = f"{job.title} {job.location or ''} {job.description or ''}".lower()
        if params.remote_only and "remote" not in text:
            return False
        if params.india_only:
            loc = (job.location or "").lower()
            india_tokens = [
                "india",
                "bangalore",
                "bengaluru",
                "hyderabad",
                "pune",
                "chennai",
                "noida",
                "gurgaon",
                "gurugram",
                "mumbai",
            ]
            if not any(t in loc or t in text for t in india_tokens) and "remote" not in text:
                return False
        return True

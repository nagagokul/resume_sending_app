from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

from app.jobsources.base import FetchJobsParams, JobSource, RawJob

logger = structlog.get_logger()

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseJobSource(JobSource):
    """Public Greenhouse Job Board API — no auth required for public boards."""

    name = "greenhouse"
    display_name = "Greenhouse"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch_jobs(self, params: FetchJobsParams) -> list[RawJob]:
        boards = params.board_tokens or []
        jobs: list[RawJob] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for board in boards:
                try:
                    board_jobs = await self._fetch_board(client, board, params)
                    jobs.extend(board_jobs)
                    if len(jobs) >= params.limit:
                        break
                except httpx.HTTPError as exc:
                    logger.warning("greenhouse_board_failed", board=board, error=str(exc))
        return jobs[: params.limit]

    async def fetch_job(self, source_job_id: str, **kwargs: Any) -> RawJob | None:
        board = kwargs.get("board_token")
        if not board:
            return None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{GREENHOUSE_API}/{board}/jobs/{source_job_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._map_job(resp.json(), board)

    async def _fetch_board(
        self, client: httpx.AsyncClient, board: str, params: FetchJobsParams
    ) -> list[RawJob]:
        resp = await client.get(f"{GREENHOUSE_API}/{board}/jobs", params={"content": "true"})
        if resp.status_code == 404:
            logger.info("greenhouse_board_not_found", board=board)
            return []
        resp.raise_for_status()
        data = resp.json()
        company_name = board.replace("-", " ").title()
        results: list[RawJob] = []
        for item in data.get("jobs", []):
            raw = self._map_job(item, board, company_name=company_name)
            if self._matches_filters(raw, params):
                results.append(raw)
        return results

    def _map_job(self, item: dict[str, Any], board: str, company_name: str | None = None) -> RawJob:
        loc_parts = []
        for loc in item.get("offices") or []:
            if isinstance(loc, dict) and loc.get("name"):
                loc_parts.append(loc["name"])
        if item.get("location"):
            loc = item["location"]
            if isinstance(loc, dict):
                loc_parts.append(loc.get("name") or "")
            elif isinstance(loc, str):
                loc_parts.append(loc)
        location = ", ".join(p for p in loc_parts if p) or None
        posted = None
        if item.get("updated_at"):
            try:
                posted = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                posted = None
        return RawJob(
            source=self.name,
            source_job_id=str(item.get("id")),
            company=company_name or board,
            title=item.get("title") or "Untitled",
            description=item.get("content") or item.get("absolute_url"),
            location=location,
            application_url=item.get("absolute_url"),
            employment_type=None,
            posted_at=posted,
            updated_at=posted,
            salary=None,
            raw_payload={"board": board, **{k: v for k, v in item.items() if k != "content"}},
        )

    def _matches_filters(self, job: RawJob, params: FetchJobsParams) -> bool:
        text = f"{job.title} {job.location or ''} {job.description or ''}".lower()
        if params.query and params.query.lower() not in text:
            # Soft match: keep software-related if query is engineering default
            pass
        if params.locations:
            loc = (job.location or "").lower()
            if not any(l.lower() in loc or l.lower() in text for l in params.locations):
                # Also allow remote for India+remote searches
                if not (params.remote_only or "remote" in text):
                    if params.india_only and not any(
                        c in loc for c in ["india", "bangalore", "bengaluru", "hyderabad", "pune", "chennai"]
                    ):
                        return False
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

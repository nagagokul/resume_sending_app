import pytest
from pytest_httpx import HTTPXMock

from app.jobsources.base import FetchJobsParams
from app.jobsources.greenhouse import GreenhouseJobSource
from app.jobsources.lever import LeverJobSource


@pytest.mark.asyncio
async def test_greenhouse_maps_public_jobs(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true",
        json={
            "jobs": [
                {
                    "id": 101,
                    "title": "Senior Software Engineer - Networking",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
                    "updated_at": "2026-08-01T10:00:00Z",
                    "location": {"name": "Bengaluru, India"},
                    "content": "C++ Linux networking remote possible",
                    "offices": [{"name": "Bengaluru"}],
                }
            ]
        },
    )
    source = GreenhouseJobSource()
    jobs = await source.fetch_jobs(
        FetchJobsParams(board_tokens=["acme"], india_only=True, limit=10)
    )
    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"
    assert jobs[0].source_job_id == "101"
    assert "Bengaluru" in (jobs[0].location or "")
    assert jobs[0].application_url.endswith("/101")


@pytest.mark.asyncio
async def test_lever_maps_public_jobs(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lever.co/v0/postings/acmecorp?mode=json",
        json=[
            {
                "id": "abc-123",
                "text": "Embedded Software Engineer",
                "hostedUrl": "https://jobs.lever.co/acmecorp/abc-123",
                "createdAt": 1722470400000,
                "categories": {"location": "Remote - India", "commitment": "Full-time"},
                "descriptionPlain": "C Linux device drivers PTP",
            }
        ],
    )
    source = LeverJobSource()
    jobs = await source.fetch_jobs(
        FetchJobsParams(company_tokens=["acmecorp"], india_only=True, limit=10)
    )
    assert len(jobs) == 1
    assert jobs[0].source == "lever"
    assert jobs[0].source_job_id == "abc-123"
    assert "Remote" in (jobs[0].location or "")
    assert "device drivers" in (jobs[0].description or "").lower() or "PTP" in (jobs[0].description or "")


@pytest.mark.asyncio
async def test_greenhouse_skips_missing_board(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://boards-api.greenhouse.io/v1/boards/does-not-exist/jobs?content=true",
        status_code=404,
    )
    source = GreenhouseJobSource()
    jobs = await source.fetch_jobs(FetchJobsParams(board_tokens=["does-not-exist"], limit=5))
    assert jobs == []

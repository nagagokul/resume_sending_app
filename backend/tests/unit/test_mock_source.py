import pytest

from app.jobsources import get_job_source, register_job_source
from app.jobsources.base import FetchJobsParams, JobSource, RawJob


class MockJobSource(JobSource):
    """Deterministic in-memory source for tests — no live network."""

    name = "mock"
    display_name = "Mock"

    def __init__(self, jobs: list[RawJob] | None = None) -> None:
        self._jobs = jobs or []

    async def fetch_jobs(self, params: FetchJobsParams) -> list[RawJob]:
        return self._jobs[: params.limit]

    async def fetch_job(self, source_job_id: str, **kwargs) -> RawJob | None:
        for job in self._jobs:
            if job.source_job_id == source_job_id:
                return job
        return None


@pytest.mark.asyncio
async def test_mock_job_source_returns_seeded_jobs():
    mock = MockJobSource(
        [
            RawJob(
                source="mock",
                source_job_id="m1",
                company="MockCorp",
                title="Senior Linux Engineer",
                location="Remote - India",
                description="C++ Linux networking",
                application_url="https://example.com/jobs/m1",
            )
        ]
    )
    register_job_source(mock)
    source = get_job_source("mock")
    jobs = await source.fetch_jobs(FetchJobsParams(limit=10))
    assert len(jobs) == 1
    assert jobs[0].company == "MockCorp"

from __future__ import annotations

from app.jobsources.base import JobSource
from app.jobsources.greenhouse import GreenhouseJobSource
from app.jobsources.lever import LeverJobSource
from app.jobsources.manual import ManualJobSource

_REGISTRY: dict[str, JobSource] = {
    "greenhouse": GreenhouseJobSource(),
    "lever": LeverJobSource(),
    "manual": ManualJobSource(),
}


def get_job_source(name: str) -> JobSource:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown job source: {name}") from exc


def list_job_sources() -> list[JobSource]:
    return list(_REGISTRY.values())


def register_job_source(source: JobSource) -> None:
    _REGISTRY[source.name] = source

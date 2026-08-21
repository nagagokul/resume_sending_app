from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.jobsources import get_job_source, list_job_sources
from app.jobsources.base import FetchJobsParams, RawJob
from app.models.job import Company, Job, JobRequirement, JobSource
from app.utils.normalize import (
    detect_remote_type,
    extract_skills_from_text,
    infer_seniority,
    is_india_location,
    normalize_skill,
    normalize_title,
)

logger = structlog.get_logger()


async def ensure_job_sources(db: AsyncSession) -> None:
    for src in list_job_sources():
        existing = await db.execute(select(JobSource).where(JobSource.name == src.name))
        if existing.scalar_one_or_none() is None:
            db.add(
                JobSource(
                    name=src.name,
                    display_name=src.display_name,
                    is_active=True,
                    config={},
                )
            )
    await db.flush()


async def discover_jobs(
    db: AsyncSession,
    *,
    sources: list[str] | None = None,
    india_and_remote: bool = True,
    limit: int = 200,
    greenhouse_boards: list[str] | None = None,
    lever_companies: list[str] | None = None,
    query: str | None = None,
) -> dict:
    settings = get_settings()
    await ensure_job_sources(db)

    source_names = sources or ["greenhouse", "lever"]
    params = FetchJobsParams(
        query=query or "software engineer",
        india_only=india_and_remote,
        remote_only=False,
        limit=limit,
        board_tokens=greenhouse_boards or settings.greenhouse_boards,
        company_tokens=lever_companies or settings.lever_companies,
        locations=[
            "India",
            "Bangalore",
            "Bengaluru",
            "Hyderabad",
            "Pune",
            "Chennai",
            "Noida",
            "Gurgaon",
            "Gurugram",
            "Mumbai",
            "Remote",
        ],
    )

    fetched = 0
    created = 0
    updated = 0
    duplicates = 0

    for name in source_names:
        source = get_job_source(name)
        try:
            raw_jobs = await source.fetch_jobs(params)
        except Exception as exc:
            logger.exception("job_source_fetch_failed", source=name, error=str(exc))
            continue

        src_row = (
            await db.execute(select(JobSource).where(JobSource.name == name))
        ).scalar_one()
        src_row.last_run_at = datetime.now(timezone.utc)
        src_row.last_status = "ok"

        for raw in raw_jobs:
            fetched += 1
            result = await upsert_job(db, raw, src_row)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            elif result == "duplicate":
                duplicates += 1

    await db.flush()
    return {
        "fetched": fetched,
        "created": created,
        "updated": updated,
        "duplicates": duplicates,
        "sources": source_names,
    }


async def upsert_job(db: AsyncSession, raw: RawJob, source_row: JobSource | None = None) -> str:
    content_hash = _content_hash(raw)
    existing = await db.execute(
        select(Job).where(Job.source == raw.source, Job.source_job_id == raw.source_job_id)
    )
    job = existing.scalar_one_or_none()

    # Dedup by application URL
    if job is None and raw.application_url:
        by_url = await db.execute(
            select(Job).where(Job.application_url == raw.application_url, Job.duplicate_of_id.is_(None))
        )
        url_match = by_url.scalar_one_or_none()
        if url_match is not None:
            # Store as duplicate pointer if different source
            dup = Job(
                company=raw.company,
                title=raw.title,
                normalized_title=normalize_title(raw.title),
                seniority=infer_seniority(raw.title),
                description=raw.description,
                location=raw.location,
                remote_type=detect_remote_type(raw.location, raw.description),
                is_india=is_india_location(raw.location),
                salary=raw.salary,
                employment_type=raw.employment_type,
                posted_at=raw.posted_at,
                application_url=raw.application_url,
                source=raw.source,
                source_job_id=raw.source_job_id,
                source_id=source_row.id if source_row else None,
                raw_payload=raw.raw_payload,
                content_hash=content_hash,
                duplicate_of_id=url_match.id,
                is_active=False,
            )
            db.add(dup)
            return "duplicate"

    # Soft dedup by company + normalized title + location
    if job is None:
        soft = await db.execute(
            select(Job).where(
                Job.company == raw.company,
                Job.normalized_title == normalize_title(raw.title),
                Job.location == raw.location,
                Job.duplicate_of_id.is_(None),
                Job.is_active.is_(True),
            )
        )
        soft_match = soft.scalar_one_or_none()
        if soft_match is not None and soft_match.source != raw.source:
            job_dup = _build_job(raw, source_row, content_hash)
            job_dup.duplicate_of_id = soft_match.id
            job_dup.is_active = False
            db.add(job_dup)
            return "duplicate"

    company = await _get_or_create_company(db, raw.company)

    if job is None:
        job = _build_job(raw, source_row, content_hash)
        job.company_id = company.id
        db.add(job)
        await db.flush()
        await _sync_requirements(db, job)
        return "created"

    job.title = raw.title
    job.normalized_title = normalize_title(raw.title)
    job.seniority = infer_seniority(raw.title)
    job.description = raw.description
    job.location = raw.location
    job.remote_type = detect_remote_type(raw.location, raw.description)
    job.is_india = is_india_location(raw.location)
    job.salary = raw.salary
    job.employment_type = raw.employment_type
    job.posted_at = raw.posted_at or job.posted_at
    job.application_url = raw.application_url
    job.raw_payload = raw.raw_payload
    job.content_hash = content_hash
    job.company_id = company.id
    job.is_active = job.duplicate_of_id is None
    await db.flush()
    await _sync_requirements(db, job)
    return "updated"


def _build_job(raw: RawJob, source_row: JobSource | None, content_hash: str) -> Job:
    skills = extract_skills_from_text(f"{raw.title}\n{raw.description or ''}")
    return Job(
        company=raw.company,
        title=raw.title,
        normalized_title=normalize_title(raw.title),
        seniority=infer_seniority(raw.title),
        description=raw.description,
        requirements=skills,
        preferred_skills=[],
        location=raw.location,
        remote_type=detect_remote_type(raw.location, raw.description),
        is_india=is_india_location(raw.location),
        salary=raw.salary,
        employment_type=raw.employment_type,
        posted_at=raw.posted_at,
        application_url=raw.application_url,
        source=raw.source,
        source_job_id=raw.source_job_id,
        source_id=source_row.id if source_row else None,
        raw_payload=raw.raw_payload,
        content_hash=content_hash,
        is_active=True,
    )


async def _get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if company:
        return company
    company = Company(name=name)
    db.add(company)
    await db.flush()
    return company


async def _sync_requirements(db: AsyncSession, job: Job) -> None:
    # Replace requirements derived from description
    for req in list(job.job_requirements):
        await db.delete(req)
    skills = extract_skills_from_text(f"{job.title}\n{job.description or ''}")
    job.requirements = skills
    for skill in skills:
        db.add(
            JobRequirement(
                job_id=job.id,
                skill=skill,
                normalized_skill=normalize_skill(skill),
                is_required=True,
                category=None,
            )
        )


def _content_hash(raw: RawJob) -> str:
    blob = f"{raw.company}|{raw.title}|{raw.location}|{(raw.description or '')[:2000]}"
    return hashlib.sha256(blob.encode()).hexdigest()


async def add_manual_job(
    db: AsyncSession,
    *,
    url: str,
    title: str | None = None,
    company: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> Job:
    await ensure_job_sources(db)
    source = get_job_source("manual")
    raw = await source.fetch_job(
        url,
        url=url,
        title=title,
        company=company,
        description=description,
        location=location,
    )
    assert raw is not None
    src_row = (await db.execute(select(JobSource).where(JobSource.name == "manual"))).scalar_one()
    await upsert_job(db, raw, src_row)
    result = await db.execute(
        select(Job).where(Job.source == "manual", Job.source_job_id == raw.source_job_id)
    )
    return result.scalar_one()

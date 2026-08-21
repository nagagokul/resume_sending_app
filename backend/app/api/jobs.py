from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationEvent, ApplicationStatus
from app.models.job import Job, JobMatch
from app.models.user import User
from app.schemas import JobDiscoverRequest, JobOut, ManualJobCreate, MatchOut
from app.services.jobs.ingestion import add_manual_job, discover_jobs
from app.services.matching.engine import match_user_jobs, match_user_to_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_out(job: Job, match: JobMatch | None = None) -> JobOut:
    return JobOut(
        id=job.id,
        company=job.company,
        title=job.title,
        normalized_title=job.normalized_title,
        seniority=job.seniority,
        description=job.description,
        requirements=job.requirements or [],
        preferred_skills=job.preferred_skills or [],
        location=job.location,
        remote_type=job.remote_type,
        is_india=job.is_india,
        salary=job.salary,
        employment_type=job.employment_type,
        posted_at=job.posted_at,
        application_url=job.application_url,
        source=job.source,
        source_job_id=job.source_job_id,
        is_active=job.is_active,
        match_score=match.score if match else None,
        match_classification=match.classification if match else None,
        matched_skills=match.matched_skills if match else [],
        missing_skills=match.missing_skills if match else [],
        match_reasoning=match.reasoning if match else None,
    )


@router.get("", response_model=list[JobOut])
async def list_jobs(
    classification: str | None = None,
    shortlisted: bool | None = None,
    min_score: float | None = None,
    source: str | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    stmt = (
        select(Job, JobMatch)
        .outerjoin(JobMatch, (JobMatch.job_id == Job.id) & (JobMatch.user_id == user.id))
        .where(Job.is_active.is_(True), Job.duplicate_of_id.is_(None))
    )
    if classification:
        stmt = stmt.where(JobMatch.classification == classification)
    if shortlisted is True:
        stmt = stmt.where(JobMatch.is_shortlisted.is_(True))
    if min_score is not None:
        stmt = stmt.where(JobMatch.score >= min_score)
    if source:
        stmt = stmt.where(Job.source == source)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Job.title.ilike(like) | Job.company.ilike(like) | Job.location.ilike(like))
    stmt = stmt.order_by(JobMatch.score.desc().nullslast(), Job.posted_at.desc().nullslast())
    stmt = stmt.offset(offset).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [_job_to_out(job, match) for job, match in rows]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    match = (
        await db.execute(select(JobMatch).where(JobMatch.job_id == job.id, JobMatch.user_id == user.id))
    ).scalar_one_or_none()
    return _job_to_out(job, match)


@router.post("/discover")
async def discover(
    payload: JobDiscoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stats = await discover_jobs(
        db,
        sources=payload.sources,
        india_and_remote=payload.india_and_remote,
        limit=payload.limit,
        greenhouse_boards=payload.greenhouse_boards,
        lever_companies=payload.lever_companies,
        query=payload.query,
    )
    matched = 0
    if payload.run_matching:
        matched = await match_user_jobs(db, user, limit=payload.limit)
    return {**stats, "matched": matched}


@router.post("/manual", response_model=JobOut)
async def create_manual_job(
    payload: ManualJobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    job = await add_manual_job(
        db,
        url=payload.url,
        title=payload.title,
        company=payload.company,
        description=payload.description,
        location=payload.location,
    )
    match = await match_user_to_job(db, user, job)
    return _job_to_out(job, match)


@router.post("/{job_id}/shortlist", response_model=MatchOut)
async def shortlist_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobMatch:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    match = await match_user_to_job(db, user, job)
    match.is_shortlisted = True
    match.is_ignored = False

    # Ensure application shell exists
    existing = await db.execute(
        select(Application).where(Application.user_id == user.id, Application.job_id == job.id)
    )
    app = existing.scalar_one_or_none()
    if app is None:
        app = Application(
            user_id=user.id,
            job_id=job.id,
            status=ApplicationStatus.SHORTLISTED.value,
        )
        db.add(app)
        await db.flush()
        db.add(
            ApplicationEvent(
                application_id=app.id,
                event_type="shortlisted",
                message="Job shortlisted",
            )
        )
    elif app.status == ApplicationStatus.DISCOVERED.value:
        app.status = ApplicationStatus.SHORTLISTED.value

    await db.flush()
    return match


@router.post("/{job_id}/ignore", response_model=MatchOut)
async def ignore_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobMatch:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    match = await match_user_to_job(db, user, job)
    match.is_ignored = True
    match.is_shortlisted = False
    await db.flush()
    return match


@router.post("/{job_id}/match", response_model=MatchOut)
async def rematch_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobMatch:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return await match_user_to_job(db, user, job)


@router.post("/{job_id}/tailor-resume")
async def tailor_resume(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy.orm import selectinload

    from app.models.candidate import CandidateProfile
    from app.models.resume import Resume, ResumeVersion
    from app.services.resume.tailor import analyze_ats, tailor_resume_from_profile

    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = (
        await db.execute(
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user.id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
            )
            .order_by(CandidateProfile.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=400, detail="Upload and parse a resume first")

    content = tailor_resume_from_profile(profile, job)
    resume = (
        await db.execute(
            select(Resume)
            .where(Resume.user_id == user.id, Resume.is_primary.is_(True))
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=400, detail="No resume on file")

    ats = analyze_ats(resume.raw_text or "", job)
    version = ResumeVersion(
        resume_id=resume.id,
        job_id=job.id,
        content=content,
        plain_text=str(content),
        model="deterministic-v1",
        prompt_version="phase6-reorder-v1",
        ats_score=int(ats["ats_score"]),
        evidence_map=content.get("evidence_map") or {},
    )
    db.add(version)
    await db.flush()
    return {
        "resume_version_id": str(version.id),
        "content": content,
        "ats": ats,
    }


@router.post("/match-all")
async def rematch_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 200,
) -> dict:
    count = await match_user_jobs(db, user, limit=limit)
    return {"matched": count}

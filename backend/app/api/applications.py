from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationEvent, ApplicationStatus, FollowUp
from app.models.job import Job, JobMatch
from app.models.user import User
from app.schemas import AnalyticsOut, ApplicationOut, ApplicationUpdate

router = APIRouter(tags=["applications"])


@router.post("/applications/prepare", response_model=ApplicationOut)
async def prepare_application(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Application:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await db.execute(
        select(Application).where(Application.user_id == user.id, Application.job_id == job.id)
    )
    app = existing.scalar_one_or_none()
    if app is None:
        app = Application(user_id=user.id, job_id=job.id)
        db.add(app)
        await db.flush()

    app.status = ApplicationStatus.PREPARING.value
    app.risks = [
        "Never fabricate experience or credentials.",
        "CAPTCHA/MFA must be completed manually.",
        "Review all autofilled fields before submit.",
    ]
    db.add(
        ApplicationEvent(
            application_id=app.id,
            event_type="preparing",
            message="Application preparation started",
            payload={"application_url": job.application_url},
        )
    )
    await db.flush()
    return app


@router.get("/applications", response_model=list[ApplicationOut])
async def list_applications(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Application]:
    stmt = select(Application).where(Application.user_id == user.id)
    if status:
        stmt = stmt.where(Application.status == status)
    stmt = stmt.order_by(Application.updated_at.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.get("/applications/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Application:
    app = (
        await db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user.id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Application:
    app = (
        await db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user.id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if payload.status is not None:
        app.status = payload.status
        db.add(
            ApplicationEvent(
                application_id=app.id,
                event_type="status_change",
                message=f"Status → {payload.status}",
            )
        )
    if payload.notes is not None:
        app.notes = payload.notes
    if payload.cover_letter is not None:
        app.cover_letter = payload.cover_letter
    if payload.follow_up_at is not None:
        app.follow_up_at = payload.follow_up_at
    if payload.user_confirmed is not None:
        app.user_confirmed = payload.user_confirmed
    await db.flush()
    return app


@router.post("/applications/{application_id}/submit", response_model=ApplicationOut)
async def submit_application(
    application_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Application:
    """Mark as applied after explicit user confirmation. Does not auto-submit forms."""
    app = (
        await db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user.id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if not app.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit Review & Apply confirmation required before submission tracking",
        )
    now = datetime.now(timezone.utc)
    app.status = ApplicationStatus.APPLIED.value
    app.applied_at = now
    app.follow_up_at = now + timedelta(days=7)
    app.expected_response_at = now + timedelta(days=14)
    db.add(
        ApplicationEvent(
            application_id=app.id,
            event_type="applied",
            message="User confirmed application submitted on official site",
        )
    )
    db.add(
        FollowUp(
            application_id=app.id,
            due_at=app.follow_up_at,
            note="Follow up if no response",
        )
    )
    await db.flush()
    return app


@router.get("/analytics", response_model=AnalyticsOut)
async def analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOut:
    jobs_discovered = (
        await db.execute(
            select(func.count()).select_from(Job).where(Job.is_active.is_(True), Job.duplicate_of_id.is_(None))
        )
    ).scalar() or 0
    jobs_shortlisted = (
        await db.execute(
            select(func.count()).select_from(JobMatch).where(
                JobMatch.user_id == user.id, JobMatch.is_shortlisted.is_(True)
            )
        )
    ).scalar() or 0

    async def count_status(*statuses: str) -> int:
        return (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.user_id == user.id, Application.status.in_(statuses))
            )
        ).scalar() or 0

    submitted = await count_status(ApplicationStatus.APPLIED.value, ApplicationStatus.OA.value,
                                   ApplicationStatus.INTERVIEW.value, ApplicationStatus.TECHNICAL_INTERVIEW.value,
                                   ApplicationStatus.HR.value, ApplicationStatus.OFFER.value,
                                   ApplicationStatus.REJECTED.value, ApplicationStatus.NO_RESPONSE.value)
    oa = await count_status(ApplicationStatus.OA.value)
    interviews = await count_status(
        ApplicationStatus.INTERVIEW.value,
        ApplicationStatus.TECHNICAL_INTERVIEW.value,
        ApplicationStatus.HR.value,
    )
    offers = await count_status(ApplicationStatus.OFFER.value)
    rejections = await count_status(ApplicationStatus.REJECTED.value)

    def rate(num: int, den: int) -> float:
        return round((num / den) * 100, 1) if den else 0.0

    return AnalyticsOut(
        jobs_discovered=jobs_discovered,
        jobs_shortlisted=jobs_shortlisted,
        applications_submitted=submitted,
        oa_received=oa,
        interviews=interviews,
        offers=offers,
        rejections=rejections,
        application_to_oa_rate=rate(oa, submitted),
        application_to_interview_rate=rate(interviews, submitted),
        application_to_offer_rate=rate(offers, submitted),
    )

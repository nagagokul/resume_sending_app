from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationStatus, FollowUp
from app.models.job import JobMatch
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    excellent = (
        await db.execute(
            select(func.count()).select_from(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.classification == "excellent",
                JobMatch.is_ignored.is_(False),
            )
        )
    ).scalar() or 0
    strong = (
        await db.execute(
            select(func.count()).select_from(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.classification == "strong",
                JobMatch.is_ignored.is_(False),
            )
        )
    ).scalar() or 0
    applications = (
        await db.execute(
            select(func.count()).select_from(Application).where(Application.user_id == user.id)
        )
    ).scalar() or 0
    applied = (
        await db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user.id,
                Application.status.in_(
                    [
                        ApplicationStatus.APPLIED.value,
                        ApplicationStatus.OA.value,
                        ApplicationStatus.INTERVIEW.value,
                        ApplicationStatus.OFFER.value,
                    ]
                ),
            )
        )
    ).scalar() or 0
    followups = (
        await db.execute(
            select(FollowUp)
            .join(Application, Application.id == FollowUp.application_id)
            .where(Application.user_id == user.id, FollowUp.completed.is_(False))
            .order_by(FollowUp.due_at.asc())
            .limit(10)
        )
    ).scalars().all()

    top_matches = (
        await db.execute(
            select(JobMatch)
            .where(JobMatch.user_id == user.id, JobMatch.is_ignored.is_(False))
            .order_by(JobMatch.score.desc())
            .limit(5)
        )
    ).scalars().all()

    return {
        "excellent_matches": excellent,
        "strong_matches": strong,
        "applications": applications,
        "applied": applied,
        "conversion_rate": round((applied / applications) * 100, 1) if applications else 0.0,
        "upcoming_followups": [
            {"id": str(f.id), "due_at": f.due_at.isoformat(), "note": f.note} for f in followups
        ],
        "top_matches": [
            {
                "job_id": str(m.job_id),
                "score": m.score,
                "classification": m.classification,
                "reasoning": m.reasoning,
            }
            for m in top_matches
        ],
    }

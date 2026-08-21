from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.candidate import CandidateProfile
from app.models.resume import Resume
from app.models.user import User
from app.schemas import CandidateProfileOut, ResumeOut
from app.services.resume.service import reanalyze_resume, save_and_parse_resume

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Resume:
    try:
        resume = await save_and_parse_resume(db, user, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to parse resume: {exc}"
        ) from exc
    return resume


@router.get("", response_model=list[ResumeOut])
async def list_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Resume]:
    result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/profile", response_model=CandidateProfileOut | None)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfile | None:
    result = await db.execute(
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user.id)
        .options(
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.experiences),
        )
        .order_by(CandidateProfile.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(
    resume_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Resume:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.post("/analyze", response_model=ResumeOut)
async def analyze_resume(
    resume_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Resume:
    if resume_id:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
        )
    else:
        result = await db.execute(
            select(Resume)
            .where(Resume.user_id == user.id, Resume.is_primary.is_(True))
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    try:
        return await reanalyze_resume(db, resume, user)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

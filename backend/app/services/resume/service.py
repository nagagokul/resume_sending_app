from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from fastapi import UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.candidate import (
    CandidateFact,
    CandidateProfile,
    Education,
    Experience,
    FactStatus,
    Project,
    Skill,
)
from app.models.resume import Resume
from app.models.user import User
from app.services.resume.extract_text import extract_text_from_file
from app.services.resume.parser import StructuredResume, parse_resume_text
from app.utils.normalize import normalize_skill

logger = structlog.get_logger()


async def save_and_parse_resume(
    db: AsyncSession,
    user: User,
    upload: UploadFile,
) -> Resume:
    settings = get_settings()
    filename = upload.filename or "resume.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {settings.allowed_extensions}")

    data = await upload.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"File exceeds max size of {settings.max_upload_size_mb}MB")

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{user.id}_{uuid.uuid4().hex}{suffix}"
    dest = upload_root / stored_name
    dest.write_bytes(data)

    # Unset previous primary
    await db.execute(
        update(Resume).where(Resume.user_id == user.id, Resume.is_primary.is_(True)).values(is_primary=False)
    )

    resume = Resume(
        user_id=user.id,
        original_filename=filename,
        file_path=str(dest),
        content_type=upload.content_type or "application/octet-stream",
        parse_status="pending",
        is_primary=True,
    )
    db.add(resume)
    await db.flush()

    try:
        raw_text = extract_text_from_file(dest, resume.content_type)
        structured = parse_resume_text(raw_text)
        resume.raw_text = raw_text
        resume.structured_json = structured.model_dump()
        resume.parse_status = "parsed"
        profile = await upsert_candidate_profile(db, user, resume, structured)
        await db.flush()
        logger.info("resume_parsed", resume_id=str(resume.id), profile_id=str(profile.id))
    except Exception as exc:
        resume.parse_status = "failed"
        resume.parse_errors = [str(exc)]
        logger.exception("resume_parse_failed", resume_id=str(resume.id))
        raise

    return resume


async def reanalyze_resume(db: AsyncSession, resume: Resume, user: User) -> Resume:
    if not resume.raw_text:
        resume.raw_text = extract_text_from_file(resume.file_path, resume.content_type)
    structured = parse_resume_text(resume.raw_text)
    resume.structured_json = structured.model_dump()
    resume.parse_status = "parsed"
    await upsert_candidate_profile(db, user, resume, structured)
    await db.flush()
    return resume


async def upsert_candidate_profile(
    db: AsyncSession,
    user: User,
    resume: Resume,
    structured: StructuredResume,
) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user.id, CandidateProfile.resume_id == resume.id)
        .options(
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.facts),
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user.id, resume_id=resume.id)
        db.add(profile)
        await db.flush()
    else:
        # Clear existing related rows for rebuild from source of truth
        for collection in (profile.skills, profile.experiences, profile.projects, profile.education, profile.facts):
            for item in list(collection):
                await db.delete(item)
        await db.flush()

    cand = structured.candidate
    profile.full_name = _val(cand.get("name"))
    profile.email = _val(cand.get("email"))
    profile.phone = _val(cand.get("phone"))
    profile.location = _val(cand.get("location"))
    profile.summary = _val(cand.get("summary"))
    profile.structured_data = structured.model_dump()
    profile.preferences = structured.preferences or user.preferences or {}

    for skill in structured.skills:
        db.add(
            Skill(
                profile_id=profile.id,
                name=skill["name"],
                normalized_name=normalize_skill(skill.get("normalized_name") or skill["name"]),
                category=skill.get("category"),
                status=skill.get("status", FactStatus.VERIFIED.value),
                evidence=skill.get("evidence"),
            )
        )
        db.add(
            CandidateFact(
                profile_id=profile.id,
                fact_type="skill",
                content=skill["name"],
                status=skill.get("status", FactStatus.VERIFIED.value),
                source_section="skills",
                meta={"category": skill.get("category")},
            )
        )

    for exp in structured.experience:
        db.add(
            Experience(
                profile_id=profile.id,
                company=exp.get("company"),
                title=exp.get("title"),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                is_current=bool(exp.get("is_current")),
                responsibilities=exp.get("responsibilities") or [],
                technologies=exp.get("technologies") or [],
                status=exp.get("status", FactStatus.VERIFIED.value),
                raw_text=exp.get("raw_text"),
            )
        )
        evidence = exp.get("raw_text") or f"{exp.get('title')} at {exp.get('company')}"
        db.add(
            CandidateFact(
                profile_id=profile.id,
                fact_type="experience",
                content=evidence,
                status=exp.get("status", FactStatus.VERIFIED.value),
                source_section="experience",
                meta={"company": exp.get("company"), "title": exp.get("title")},
            )
        )

    for proj in structured.projects:
        db.add(
            Project(
                profile_id=profile.id,
                name=proj.get("name"),
                description=proj.get("description"),
                technologies=proj.get("technologies") or [],
                achievements=proj.get("achievements") or [],
                status=proj.get("status", FactStatus.VERIFIED.value),
            )
        )
        if proj.get("description") or proj.get("name"):
            db.add(
                CandidateFact(
                    profile_id=profile.id,
                    fact_type="project",
                    content=proj.get("description") or proj.get("name") or "",
                    status=proj.get("status", FactStatus.VERIFIED.value),
                    source_section="projects",
                    meta={"name": proj.get("name")},
                )
            )

    for edu in structured.education:
        db.add(
            Education(
                profile_id=profile.id,
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                field=edu.get("field"),
                start_date=edu.get("start_date"),
                end_date=edu.get("end_date"),
                status=edu.get("status", FactStatus.VERIFIED.value),
            )
        )

    for ach in structured.achievements:
        db.add(
            CandidateFact(
                profile_id=profile.id,
                fact_type="achievement",
                content=ach,
                status=FactStatus.VERIFIED.value,
                source_section="achievements",
            )
        )

    await db.flush()
    return profile


def _val(field: dict | None) -> str | None:
    if not field:
        return None
    return field.get("value")

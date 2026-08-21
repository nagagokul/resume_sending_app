from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile
from app.models.job import Job, JobMatch
from app.models.user import User
from app.utils.normalize import normalize_skill

DEFAULT_WEIGHTS = {
    "semantic_skill": 0.30,
    "required_skill_coverage": 0.20,
    "experience_similarity": 0.15,
    "domain_similarity": 0.10,
    "seniority_compatibility": 0.10,
    "location_compatibility": 0.05,
    "compensation_compatibility": 0.05,
    "career_preference": 0.05,
}

DOMAIN_KEYWORDS = {
    "networking",
    "network",
    "telecom",
    "embedded",
    "linux",
    "kernel",
    "driver",
    "ptp",
    "optical",
    "protocol",
    "systems",
    "infrastructure",
    "platform",
}


@dataclass
class MatchResult:
    score: float
    classification: str
    matched_skills: list[str]
    missing_skills: list[str]
    evidence: list[str]
    concerns: list[str]
    reasoning: str
    score_breakdown: dict


def classify_score(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 80:
        return "strong"
    if score >= 70:
        return "possible"
    if score >= 60:
        return "weak"
    return "skip"


def compute_match(
    *,
    candidate_skills: set[str],
    candidate_titles: list[str],
    candidate_text: str,
    candidate_location: str | None,
    preferences: dict,
    job: Job,
    weights: dict | None = None,
) -> MatchResult:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    job_skills = {normalize_skill(s) for s in (job.requirements or [])}
    # Also pull from description tokens already normalized in requirements
    cand_norm = {normalize_skill(s) for s in candidate_skills}

    matched = sorted(job_skills & cand_norm)
    missing = sorted(job_skills - cand_norm)

    coverage = (len(matched) / len(job_skills)) if job_skills else 0.5
    # Semantic proxy: Jaccard over skills + shared domain tokens
    union = cand_norm | job_skills
    jaccard = (len(cand_norm & job_skills) / len(union)) if union else 0.0
    job_text = f"{job.title} {job.description or ''}".lower()
    cand_lower = candidate_text.lower()
    domain_hits = sum(1 for d in DOMAIN_KEYWORDS if d in job_text and d in cand_lower)
    domain_score = min(1.0, domain_hits / 3.0)

    # Experience / title similarity
    title_l = (job.normalized_title or job.title or "").lower()
    exp_score = 0.4
    for t in candidate_titles:
        if not t:
            continue
        t_l = t.lower()
        overlap = set(t_l.split()) & set(title_l.split())
        if overlap:
            exp_score = max(exp_score, min(1.0, len(overlap) / max(3, len(title_l.split()))))
        if "software" in t_l and "software" in title_l:
            exp_score = max(exp_score, 0.7)

    # Seniority
    seniority = (job.seniority or "MID").upper()
    pref_seniority = (preferences.get("seniority") or "SENIOR").upper()
    seniority_map = {"JUNIOR": 1, "MID": 2, "SENIOR": 3, "STAFF": 4, "PRINCIPAL": 5}
    diff = abs(seniority_map.get(seniority, 2) - seniority_map.get(pref_seniority, 3))
    seniority_score = max(0.0, 1.0 - diff * 0.25)

    # Location: India cities + remote
    loc_score = 0.5
    job_loc = (job.location or "").lower()
    cand_loc = (candidate_location or "").lower()
    if job.remote_type == "remote":
        loc_score = 1.0
    elif job.is_india:
        loc_score = 0.9
        if cand_loc and cand_loc in job_loc:
            loc_score = 1.0
    elif cand_loc and cand_loc in job_loc:
        loc_score = 0.85

    # Compensation unknown → neutral
    comp_score = 0.7 if not job.salary else 0.8

    # Career preference: role keywords
    preferred_roles = [r.lower() for r in preferences.get("target_roles", [])]
    pref_score = 0.6
    if preferred_roles:
        pref_score = 1.0 if any(r in title_l for r in preferred_roles) else 0.4
    elif any(k in title_l for k in ["software", "systems", "embedded", "network", "linux", "platform"]):
        pref_score = 0.85

    breakdown = {
        "semantic_skill": round(jaccard * 100, 2),
        "required_skill_coverage": round(coverage * 100, 2),
        "experience_similarity": round(exp_score * 100, 2),
        "domain_similarity": round(domain_score * 100, 2),
        "seniority_compatibility": round(seniority_score * 100, 2),
        "location_compatibility": round(loc_score * 100, 2),
        "compensation_compatibility": round(comp_score * 100, 2),
        "career_preference": round(pref_score * 100, 2),
    }

    score = (
        w["semantic_skill"] * jaccard
        + w["required_skill_coverage"] * coverage
        + w["experience_similarity"] * exp_score
        + w["domain_similarity"] * domain_score
        + w["seniority_compatibility"] * seniority_score
        + w["location_compatibility"] * loc_score
        + w["compensation_compatibility"] * comp_score
        + w["career_preference"] * pref_score
    ) * 100

    score = round(min(100.0, max(0.0, score)), 1)
    classification = classify_score(score)

    evidence = [f"Matched skill: {s}" for s in matched[:12]]
    if domain_hits:
        evidence.append(f"Shared domain signals: {domain_hits}")
    if job.remote_type == "remote" or job.is_india:
        evidence.append(f"Location fit: {job.location or job.remote_type}")

    concerns = [f"Missing skill: {s}" for s in missing[:12]]
    if seniority == "PRINCIPAL" and pref_seniority == "SENIOR":
        concerns.append("Role seniority may be above current preference")

    reasoning = (
        f"Score {score} ({classification}). "
        f"Skill coverage {breakdown['required_skill_coverage']}%, "
        f"domain {breakdown['domain_similarity']}%, "
        f"location {breakdown['location_compatibility']}%."
    )
    if missing:
        reasoning += f" Gaps: {', '.join(missing[:5])}."

    return MatchResult(
        score=score,
        classification=classification,
        matched_skills=matched,
        missing_skills=missing,
        evidence=evidence,
        concerns=concerns,
        reasoning=reasoning,
        score_breakdown=breakdown,
    )


async def match_user_to_job(db: AsyncSession, user: User, job: Job) -> JobMatch:
    profile = await _load_profile(db, user)
    weights = user.scoring_weights or {}
    preferences = (profile.preferences if profile else None) or user.preferences or {}
    if not preferences.get("target_roles"):
        preferences = {
            **preferences,
            "target_roles": [
                "senior software engineer",
                "software engineer",
                "systems software",
                "embedded",
                "network",
                "linux",
                "platform",
                "infrastructure",
            ],
            "seniority": "SENIOR",
        }

    candidate_skills = {s.normalized_name for s in (profile.skills if profile else [])}
    candidate_titles = [e.title for e in (profile.experiences if profile else []) if e.title]
    candidate_text = " ".join(
        [
            profile.summary or "",
            " ".join(candidate_skills),
            " ".join(e.raw_text or "" for e in (profile.experiences if profile else [])),
        ]
    )
    result = compute_match(
        candidate_skills=candidate_skills,
        candidate_titles=candidate_titles,
        candidate_text=candidate_text,
        candidate_location=profile.location if profile else None,
        preferences=preferences,
        job=job,
        weights=weights,
    )

    existing = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
    )
    match = existing.scalar_one_or_none()
    if match is None:
        match = JobMatch(user_id=user.id, job_id=job.id)
        db.add(match)

    match.score = result.score
    match.classification = result.classification
    match.matched_skills = result.matched_skills
    match.missing_skills = result.missing_skills
    match.evidence = result.evidence
    match.concerns = result.concerns
    match.reasoning = result.reasoning
    match.score_breakdown = result.score_breakdown
    await db.flush()
    return match


async def match_user_jobs(db: AsyncSession, user: User, limit: int = 200) -> int:
    result = await db.execute(
        select(Job)
        .where(Job.is_active.is_(True), Job.duplicate_of_id.is_(None))
        .order_by(Job.posted_at.desc().nullslast())
        .limit(limit)
    )
    jobs = result.scalars().all()
    count = 0
    for job in jobs:
        await match_user_to_job(db, user, job)
        count += 1
    return count


async def _load_profile(db: AsyncSession, user: User) -> CandidateProfile | None:
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

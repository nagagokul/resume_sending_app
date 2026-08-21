from __future__ import annotations

from app.models.candidate import CandidateProfile
from app.models.job import Job


def tailor_resume_from_profile(profile: CandidateProfile, job: Job) -> dict:
    """Reorder/emphasize verified facts only — never invent skills or employers."""
    job_skills = {s.lower() for s in (job.requirements or [])}
    skills = sorted(
        profile.skills,
        key=lambda s: (0 if s.normalized_name.lower() in job_skills else 1, s.name.lower()),
    )
    experiences = []
    for exp in profile.experiences:
        bullets = list(exp.responsibilities or [])
        # Prefer bullets mentioning job skills
        bullets.sort(
            key=lambda b: 0 if any(sk in b.lower() for sk in job_skills) else 1
        )
        experiences.append(
            {
                "title": exp.title,
                "company": exp.company,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "responsibilities": bullets,
                "technologies": exp.technologies,
                "status": exp.status,
            }
        )

    summary = profile.summary
    matched = [s.name for s in skills if s.normalized_name.lower() in job_skills]
    targeted_summary = summary
    if summary and matched:
        targeted_summary = (
            f"{summary.rstrip('.')}. Relevant strengths for this role include "
            f"{', '.join(matched[:6])}."
        )

    return {
        "candidate": {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": targeted_summary,
        },
        "skills": [
            {"name": s.name, "category": s.category, "status": s.status} for s in skills
        ],
        "experience": experiences,
        "evidence_map": {
            "skills": [s.name for s in skills],
            "note": "All statements trace to VERIFIED profile facts only.",
        },
        "job_id": str(job.id),
        "job_title": job.title,
        "company": job.company,
    }


def analyze_ats(resume_text: str, job: Job) -> dict:
    """Keyword coverage without recommending stuffing."""
    from app.utils.normalize import extract_skills_from_text

    job_skills = set(job.requirements or []) or set(
        extract_skills_from_text(f"{job.title}\n{job.description or ''}")
    )
    resume_skills = set(extract_skills_from_text(resume_text))
    matched = sorted(job_skills & resume_skills)
    missing = sorted(job_skills - resume_skills)
    coverage = (len(matched) / len(job_skills) * 100) if job_skills else 50.0
    return {
        "ats_score": round(min(100.0, coverage + (10 if matched else 0)), 1),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "weak_evidence": [],
        "potential_problems": (
            ["Resume missing several required skills"] if len(missing) > 3 else []
        ),
        "recommended_changes": [
            f"Where truthful, emphasize evidence of: {', '.join(missing[:5])}"
        ]
        if missing
        else ["Coverage looks solid for listed requirements."],
    }

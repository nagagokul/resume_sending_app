from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.models.candidate import FactStatus
from app.services.resume.extract_text import EMAIL_RE, PHONE_RE, split_sections
from app.utils.normalize import expand_compound_skill, extract_skills_from_text, normalize_skill


class StructuredResume(BaseModel):
    candidate: dict[str, Any] = Field(default_factory=dict)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


def parse_resume_text(text: str) -> StructuredResume:
    """Deterministic resume parser. Never invents experience — only extracts present text."""
    sections = split_sections(text)
    preamble = sections.get("_preamble", "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    email = _first_match(EMAIL_RE, text)
    phone = _first_phone(text)
    name = _guess_name(preamble, lines)
    location = _guess_location(preamble)

    summary = sections.get("summary") or None
    if summary:
        summary_status = FactStatus.VERIFIED.value
    else:
        summary_status = FactStatus.MISSING.value

    skills = _parse_skills(sections.get("skills", ""), text)
    experience = _parse_experience(sections.get("experience", ""))
    projects = _parse_projects(sections.get("projects", ""))
    education = _parse_education(sections.get("education", ""))
    certifications = _parse_list_section(sections.get("certifications", ""))
    achievements = [
        item["value"] for item in _parse_list_section(sections.get("achievements", ""))
    ]

    candidate = {
        "name": {"value": name, "status": FactStatus.VERIFIED.value if name else FactStatus.MISSING.value},
        "email": {"value": email, "status": FactStatus.VERIFIED.value if email else FactStatus.MISSING.value},
        "phone": {"value": phone, "status": FactStatus.VERIFIED.value if phone else FactStatus.MISSING.value},
        "location": {
            "value": location,
            "status": FactStatus.VERIFIED.value if location else FactStatus.MISSING.value,
        },
        "summary": {"value": summary, "status": summary_status},
    }

    missing = [k for k, v in candidate.items() if v["status"] == FactStatus.MISSING.value]
    if not skills:
        missing.append("skills")
    if not experience:
        missing.append("experience")

    return StructuredResume(
        candidate=candidate,
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
        certifications=certifications,
        achievements=achievements,
        preferences={},
        missing_fields=missing,
    )


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(0) if m else None


def _first_phone(text: str) -> str | None:
    for m in PHONE_RE.finditer(text):
        candidate = m.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if 10 <= len(digits) <= 15:
            return candidate
    return None


def _guess_name(preamble: str, lines: list[str]) -> str | None:
    for line in (preamble.splitlines() + lines)[:8]:
        clean = line.strip()
        if not clean or "@" in clean or EMAIL_RE.search(clean) or PHONE_RE.search(clean):
            continue
        if re.search(r"https?://|linkedin|github", clean, re.I):
            continue
        if len(clean.split()) <= 5 and re.match(r"^[A-Za-z][A-Za-z .'-]+$", clean):
            return clean
    return None


def _guess_location(preamble: str) -> str | None:
    cities = [
        "Bangalore",
        "Bengaluru",
        "Hyderabad",
        "Pune",
        "Chennai",
        "Noida",
        "Gurgaon",
        "Gurugram",
        "Mumbai",
        "Delhi",
        "India",
    ]
    for city in cities:
        if re.search(rf"\b{re.escape(city)}\b", preamble, re.I):
            return city
    m = re.search(r"\b([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)\b", preamble)
    return m.group(1) if m else None


def _parse_skills(skills_section: str, full_text: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    source_text = skills_section or full_text
    # Split on common delimiters in skills sections
    tokens: list[str] = []
    for chunk in re.split(r"[,|•·\n;/]", source_text):
        chunk = chunk.strip(" -:\t")
        if not chunk or len(chunk) > 60:
            continue
        tokens.append(chunk)

    for token in tokens:
        for skill in expand_compound_skill(token):
            norm = normalize_skill(skill)
            if len(norm) < 2:
                continue
            # Only keep if it looks like a skill token (not a sentence)
            if " " in norm and norm not in extract_skills_from_text(norm):
                # Allow multi-word known skills only
                from app.utils.normalize import KNOWN_SKILLS

                if norm not in KNOWN_SKILLS:
                    continue
            found[norm.lower()] = {
                "name": norm,
                "normalized_name": norm,
                "category": _categorize_skill(norm),
                "status": FactStatus.VERIFIED.value,
                "evidence": token,
            }

    # Also scan known skills from full resume (verified only if literally present)
    for skill in extract_skills_from_text(full_text):
        key = skill.lower()
        if key not in found:
            found[key] = {
                "name": skill,
                "normalized_name": skill,
                "category": _categorize_skill(skill),
                "status": FactStatus.VERIFIED.value,
                "evidence": skill,
            }
    return sorted(found.values(), key=lambda s: s["name"].lower())


def _categorize_skill(name: str) -> str:
    languages = {"C", "C++", "Python", "Go", "Rust", "Java", "JavaScript", "TypeScript", "Bash"}
    oses = {"Linux", "Linux Kernel", "RTOS"}
    networking = {
        "Networking",
        "Network Protocols",
        "NETCONF",
        "RESTCONF",
        "TCP/IP",
        "Sockets",
        "PTP",
        "LinuxPTP",
        "Optical Networking",
        "Telecom",
    }
    dbs = {"SQL", "PostgreSQL", "MySQL", "Redis"}
    cloud = {"AWS", "Azure", "GCP", "Docker", "Kubernetes"}
    if name in languages:
        return "language"
    if name in oses:
        return "os"
    if name in networking:
        return "networking"
    if name in dbs:
        return "database"
    if name in cloud:
        return "cloud"
    return "tool"


def _parse_experience(section: str) -> list[dict[str, Any]]:
    if not section.strip():
        return []
    blocks = re.split(r"\n(?=[A-Z][^\n]{2,80})", section)
    results: list[dict[str, Any]] = []
    date_re = re.compile(
        r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})"
        r"\s*[-–—to]+\s*"
        r"(?P<end>(?:Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}))",
        re.I,
    )
    for block in blocks:
        block = block.strip()
        if len(block) < 10:
            continue
        lines = [ln.strip(" •-\t") for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        header = lines[0]
        date_m = date_re.search(block)
        bullets = [ln for ln in lines[1:] if ln.startswith(("*", "-", "•")) or len(ln) > 40]
        # Clean bullet prefixes
        bullets = [re.sub(r"^[\*\-•]\s*", "", b) for b in bullets]
        title, company = _split_title_company(header)
        results.append(
            {
                "title": title,
                "company": company,
                "start_date": date_m.group("start") if date_m else None,
                "end_date": date_m.group("end") if date_m else None,
                "is_current": bool(date_m and re.search(r"present|current", date_m.group("end"), re.I)),
                "responsibilities": bullets,
                "technologies": extract_skills_from_text(block),
                "status": FactStatus.VERIFIED.value,
                "raw_text": block,
            }
        )
    return results


def _split_title_company(header: str) -> tuple[str | None, str | None]:
    for sep in [" at ", " @ ", " - ", " – ", " — ", " | "]:
        if sep in header:
            left, right = header.split(sep, 1)
            return left.strip(), right.strip()
    return header.strip(), None


def _parse_projects(section: str) -> list[dict[str, Any]]:
    if not section.strip():
        return []
    results = []
    for block in re.split(r"\n(?=[A-Z])", section):
        block = block.strip()
        if len(block) < 8:
            continue
        lines = [ln.strip(" •-\t") for ln in block.splitlines() if ln.strip()]
        name = lines[0]
        desc = " ".join(lines[1:]) if len(lines) > 1 else None
        results.append(
            {
                "name": name,
                "description": desc,
                "technologies": extract_skills_from_text(block),
                "achievements": [],
                "status": FactStatus.VERIFIED.value,
            }
        )
    return results


def _parse_education(section: str) -> list[dict[str, Any]]:
    if not section.strip():
        return []
    results = []
    for block in re.split(r"\n\s*\n", section):
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        results.append(
            {
                "institution": lines[0] if lines else None,
                "degree": lines[1] if len(lines) > 1 else None,
                "field": None,
                "start_date": None,
                "end_date": None,
                "status": FactStatus.VERIFIED.value,
            }
        )
    return results


def _parse_list_section(section: str) -> list[dict[str, Any]]:
    items = []
    for line in section.splitlines():
        clean = re.sub(r"^[\*\-•]\s*", "", line).strip()
        if clean:
            items.append({"value": clean, "status": FactStatus.VERIFIED.value})
    return items

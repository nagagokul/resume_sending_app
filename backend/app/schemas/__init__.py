from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    preferences: dict[str, Any] = Field(default_factory=dict)
    scoring_weights: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class ResumeOut(BaseModel):
    id: UUID
    original_filename: str
    parse_status: str
    structured_json: dict[str, Any]
    is_primary: bool
    created_at: datetime
    parse_errors: list[Any] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SkillOut(BaseModel):
    name: str
    normalized_name: str
    category: str | None
    status: str
    evidence: str | None = None

    model_config = {"from_attributes": True}


class ExperienceOut(BaseModel):
    company: str | None
    title: str | None
    start_date: str | None
    end_date: str | None
    is_current: bool
    responsibilities: list[Any] = Field(default_factory=list)
    technologies: list[Any] = Field(default_factory=list)
    status: str

    model_config = {"from_attributes": True}


class CandidateProfileOut(BaseModel):
    id: UUID
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    preferences: dict[str, Any]
    structured_data: dict[str, Any]
    skills: list[SkillOut] = Field(default_factory=list)
    experiences: list[ExperienceOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: UUID
    company: str
    title: str
    normalized_title: str | None
    seniority: str | None
    description: str | None
    requirements: list[Any]
    preferred_skills: list[Any]
    location: str | None
    remote_type: str | None
    is_india: bool
    salary: dict[str, Any] | None
    employment_type: str | None
    posted_at: datetime | None
    application_url: str | None
    source: str
    source_job_id: str
    is_active: bool
    match_score: float | None = None
    match_classification: str | None = None
    matched_skills: list[Any] = Field(default_factory=list)
    missing_skills: list[Any] = Field(default_factory=list)
    match_reasoning: str | None = None

    model_config = {"from_attributes": True}


class JobDiscoverRequest(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["greenhouse", "lever"])
    india_and_remote: bool = True
    limit: int = 100
    greenhouse_boards: list[str] | None = None
    lever_companies: list[str] | None = None
    query: str | None = None
    run_matching: bool = True


class ManualJobCreate(BaseModel):
    url: str
    title: str | None = None
    company: str | None = None
    description: str | None = None
    location: str | None = None


class MatchOut(BaseModel):
    score: float
    classification: str
    matched_skills: list[Any]
    missing_skills: list[Any]
    evidence: list[Any]
    concerns: list[Any]
    reasoning: str | None
    score_breakdown: dict[str, Any]
    is_shortlisted: bool
    is_ignored: bool

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: UUID
    job_id: UUID
    status: str
    cover_letter: str | None
    notes: str | None
    applied_at: datetime | None
    follow_up_at: datetime | None
    user_confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    cover_letter: str | None = None
    follow_up_at: datetime | None = None
    user_confirmed: bool | None = None


class AnalyticsOut(BaseModel):
    jobs_discovered: int
    jobs_shortlisted: int
    applications_submitted: int
    oa_received: int
    interviews: int
    offers: int
    rejections: int
    application_to_oa_rate: float
    application_to_interview_rate: float
    application_to_offer_rate: float


class PreferencesUpdate(BaseModel):
    preferences: dict[str, Any] | None = None
    scoring_weights: dict[str, Any] | None = None
    full_name: str | None = None

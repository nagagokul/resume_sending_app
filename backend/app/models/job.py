from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(512))
    careers_url: Mapped[str | None] = mapped_column(String(1024))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="company_rel")


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # greenhouse|lever|manual|...
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="source_rel")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("job_sources.id"))
    company: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    normalized_title: Mapped[str | None] = mapped_column(String(512), index=True)
    seniority: Mapped[str | None] = mapped_column(String(32), index=True)  # JUNIOR|MID|SENIOR|STAFF|PRINCIPAL
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    preferred_skills: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    experience_required: Mapped[str | None] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(512), index=True)
    remote_type: Mapped[str | None] = mapped_column(String(32), index=True)  # remote|hybrid|onsite|unknown
    is_india: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    salary: Mapped[dict | None] = mapped_column(JSONB)
    employment_type: Mapped[str | None] = mapped_column(String(64))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_url: Mapped[str | None] = mapped_column(String(2048), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company_rel = relationship("Company", back_populates="jobs")
    source_rel = relationship("JobSource", back_populates="jobs")
    job_requirements = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="job")
    applications = relationship("Application", back_populates="job")
    duplicate_of = relationship("Job", remote_side="Job.id")


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), index=True)
    skill: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_skill: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str | None] = mapped_column(String(64))

    job = relationship("Job", back_populates="job_requirements")


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    classification: Mapped[str] = mapped_column(String(32), index=True)  # excellent|strong|possible|weak|skip
    matched_skills: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    missing_skills: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    evidence: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    concerns: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    reasoning: Mapped[str | None] = mapped_column(Text)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_ignored: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", back_populates="matches")

"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preferences", postgresql.JSONB(), server_default="{}"),
        sa.Column("scoring_weights", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(512)),
        sa.Column("careers_url", sa.String(1024)),
        sa.Column("meta", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_name", "companies", ["name"], unique=True)

    op.create_table(
        "job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(512)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), server_default="{}"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_status", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("raw_text", sa.Text()),
        sa.Column("structured_json", postgresql.JSONB(), server_default="{}"),
        sa.Column("parse_status", sa.String(32), server_default="pending"),
        sa.Column("parse_errors", postgresql.JSONB(), server_default="[]"),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_sources.id")),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("normalized_title", sa.String(512)),
        sa.Column("seniority", sa.String(32)),
        sa.Column("description", sa.Text()),
        sa.Column("requirements", postgresql.JSONB(), server_default="[]"),
        sa.Column("preferred_skills", postgresql.JSONB(), server_default="[]"),
        sa.Column("experience_required", sa.String(128)),
        sa.Column("location", sa.String(512)),
        sa.Column("remote_type", sa.String(32)),
        sa.Column("is_india", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("salary", postgresql.JSONB()),
        sa.Column("employment_type", sa.String(64)),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at_source", sa.DateTime(timezone=True)),
        sa.Column("application_url", sa.String(2048)),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_job_id", sa.String(255), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("embedding", Vector(768)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
    )
    op.create_index("ix_jobs_company", "jobs", ["company"])
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_is_active", "jobs", ["is_active"])
    op.create_index("ix_jobs_application_url", "jobs", ["application_url"])

    op.create_table(
        "candidate_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id")),
        sa.Column("full_name", sa.String(255)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(64)),
        sa.Column("location", sa.String(255)),
        sa.Column("summary", sa.Text()),
        sa.Column("years_experience", sa.Float()),
        sa.Column("preferences", postgresql.JSONB(), server_default="{}"),
        sa.Column("structured_data", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"])

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("normalized_name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64)),
        sa.Column("status", sa.String(16), server_default="VERIFIED"),
        sa.Column("proficiency", sa.String(32)),
        sa.Column("evidence", sa.Text()),
    )
    op.create_index("ix_skills_normalized_name", "skills", ["normalized_name"])

    op.create_table(
        "experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("company", sa.String(255)),
        sa.Column("title", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("start_date", sa.String(32)),
        sa.Column("end_date", sa.String(32)),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("responsibilities", postgresql.JSONB(), server_default="[]"),
        sa.Column("technologies", postgresql.JSONB(), server_default="[]"),
        sa.Column("status", sa.String(16), server_default="VERIFIED"),
        sa.Column("raw_text", sa.Text()),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("technologies", postgresql.JSONB(), server_default="[]"),
        sa.Column("achievements", postgresql.JSONB(), server_default="[]"),
        sa.Column("status", sa.String(16), server_default="VERIFIED"),
    )

    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("institution", sa.String(255)),
        sa.Column("degree", sa.String(255)),
        sa.Column("field", sa.String(255)),
        sa.Column("start_date", sa.String(32)),
        sa.Column("end_date", sa.String(32)),
        sa.Column("status", sa.String(16), server_default="VERIFIED"),
    )

    op.create_table(
        "candidate_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("fact_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default="VERIFIED"),
        sa.Column("source_section", sa.String(128)),
        sa.Column("meta", postgresql.JSONB(), server_default="{}"),
        sa.Column("embedding", Vector(768)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_candidate_facts_fact_type", "candidate_facts", ["fact_type"])

    op.create_table(
        "job_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("skill", sa.String(128), nullable=False),
        sa.Column("normalized_skill", sa.String(128), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("category", sa.String(64)),
    )

    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("score", sa.Float(), server_default="0"),
        sa.Column("classification", sa.String(32)),
        sa.Column("matched_skills", postgresql.JSONB(), server_default="[]"),
        sa.Column("missing_skills", postgresql.JSONB(), server_default="[]"),
        sa.Column("evidence", postgresql.JSONB(), server_default="[]"),
        sa.Column("concerns", postgresql.JSONB(), server_default="[]"),
        sa.Column("reasoning", sa.Text()),
        sa.Column("score_breakdown", postgresql.JSONB(), server_default="{}"),
        sa.Column("is_shortlisted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_ignored", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),
    )
    op.create_index("ix_job_matches_score", "job_matches", ["score"])

    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("content", postgresql.JSONB(), server_default="{}"),
        sa.Column("plain_text", sa.Text()),
        sa.Column("file_path", sa.String(1024)),
        sa.Column("model", sa.String(128)),
        sa.Column("prompt_version", sa.String(64)),
        sa.Column("ats_score", sa.Integer()),
        sa.Column("evidence_map", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resume_versions.id")),
        sa.Column("status", sa.String(32), server_default="DISCOVERED"),
        sa.Column("cover_letter", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("expected_response_at", sa.DateTime(timezone=True)),
        sa.Column("follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("form_snapshot", postgresql.JSONB(), server_default="{}"),
        sa.Column("risks", postgresql.JSONB(), server_default="[]"),
        sa.Column("user_confirmed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "application_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text()),
        sa.Column("confidence", sa.String(16), server_default="YELLOW"),
        sa.Column("requires_manual_review", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("category", sa.String(64)),
        sa.Column("evidence", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "application_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("doc_type", sa.String(64)),
        sa.Column("file_path", sa.String(1024)),
        sa.Column("meta", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("event_type", sa.String(64)),
        sa.Column("message", sa.Text()),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("stage", sa.String(64)),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("prep_plan", postgresql.JSONB(), server_default="{}"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "automation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id")),
        sa.Column("run_type", sa.String(64)),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("provider", sa.String(32)),
        sa.Column("model", sa.String(128)),
        sa.Column("operation", sa.String(64)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("success", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("meta", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    for table in [
        "llm_usage",
        "automation_runs",
        "follow_ups",
        "interviews",
        "application_events",
        "application_documents",
        "application_answers",
        "applications",
        "resume_versions",
        "job_matches",
        "job_requirements",
        "candidate_facts",
        "education",
        "projects",
        "experiences",
        "skills",
        "candidate_profiles",
        "jobs",
        "resumes",
        "job_sources",
        "companies",
        "users",
    ]:
        op.drop_table(table)

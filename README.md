# Pathfind — AI Job Application Agent

Production-oriented personal job-search assistant for **India + remote** software engineering roles.
Prioritizes **high-quality matching** over mass applications. Runs **free-first** with Ollama, PostgreSQL/pgvector, Redis, and Playwright.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js, TypeScript, Tailwind, TanStack Query, React Hook Form, Zod |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic, httpx, Celery |
| Data | PostgreSQL + pgvector, Redis |
| AI | Ollama (default), optional Gemini / OpenAI-compatible |
| Browser | Playwright (assistive only — no CAPTCHA/MFA bypass) |

## Quick start

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- Backend API / OpenAPI: http://localhost:8000/docs
- Postgres: localhost:5432
- Redis: localhost:6379
- Ollama (optional profile): `docker compose --profile ai up`

### Local backend (without Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://jobagent:jobagent@localhost:5432/jobagent
export DATABASE_URL_SYNC=postgresql://jobagent:jobagent@localhost:5432/jobagent
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## Primary workflow

1. Register / sign in  
2. Upload resume (PDF / DOCX / TXT)  
3. Discover Greenhouse + Lever public jobs  
4. Review ranked matches  
5. Shortlist → Prepare → Review & Apply  
6. Track status / follow-ups / analytics  

## Phases implemented (MVP foundation)

- **Phase 1** — Resume upload, text extraction, structured parsing, candidate profile + fact statuses (`VERIFIED` / `INFERRED` / `MISSING`)
- **Phase 2** — Modular `JobSource` with Greenhouse & Lever public APIs + manual URLs
- **Phase 3–4** — Normalization, deduplication signals, hybrid scoring engine
- **Phase 5** — Jobs dashboard UI
- **Phase 8–11 scaffolding** — Application prepare/review/submit tracking, Kanban, analytics
- Full DB schema + Alembic migration for later phases (resume versions, interviews, automation, LLM usage)

Later phases (tailored resume generation, ATS, Playwright form assist, interview prep) build on the same provider-independent LLM and application models.

## Compliance

- Uses **public** Greenhouse / Lever APIs only  
- Does **not** bypass CAPTCHA, MFA, auth, robots, or anti-bot controls  
- Never fabricates candidate experience  
- Requires explicit **Review & Apply** confirmation before marking submitted  

## Tests

```bash
cd backend
pytest tests/unit -q
```

Mock job sources keep tests free of live network dependency (`pytest-httpx`).

## API highlights

- `POST /api/resume/upload`
- `GET /api/resume/profile`
- `POST /api/jobs/discover`
- `GET /api/jobs`
- `POST /api/jobs/{id}/shortlist`
- `POST /api/jobs/{id}/match`
- `POST /api/applications/prepare`
- `POST /api/applications/{id}/submit`
- `GET /api/analytics`

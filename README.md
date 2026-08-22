# Pathfind — AI Job Application Agent

Personal AI job-search and application assistant for **India + remote** software engineering roles.
Prioritizes **high-quality matching** over mass applications.

Runs **entirely on native Windows processes** — no Docker Desktop, no containers, no `docker compose`.

Free-first defaults: **Ollama** (local LLM), **PostgreSQL + pgvector**, **Redis**, **Playwright**.

---

## Prerequisites

Install these on Windows 10/11 before setup:

| Dependency | Notes |
|------------|--------|
| Python 3.11+ | Enable **Add python.exe to PATH** |
| Node.js 20+ LTS | Includes npm |
| PostgreSQL | Native Windows installer; enable **pgvector** |
| Redis | Redis for Windows, [Memurai](https://www.memurai.com/), or another Redis-compatible service on `localhost:6379` |
| Ollama | [ollama.com/download](https://ollama.com/download) for Windows |
| Git | For cloning |

Do **not** install Docker for this project.

---

## Architecture (native)

```text
Windows
 │
 ├── Next.js frontend        → http://localhost:3000
 ├── FastAPI backend         → http://127.0.0.1:8000
 ├── Celery worker           → pool=solo (Windows-safe)
 ├── PostgreSQL              → localhost:5432
 ├── Redis                   → localhost:6379
 └── Ollama                 → localhost:11434
```

---

## Installation

```powershell
git clone <repository-url>
cd resume_sending_app

# If scripts are blocked:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

.\scripts\setup.ps1
```

`setup.ps1` will:

1. Verify Python, Node, PostgreSQL, Redis, Ollama  
2. Create `.env` from `.env.example` (if missing)  
3. Create `backend\.venv` and install Python deps  
4. Install Playwright Chromium  
5. Run `npm install` in `frontend`  
6. Run `alembic upgrade head`  
7. Pull configured Ollama models (when CLI is available)

Edit `.env` and set your real PostgreSQL password **before** relying on migrations if the default does not match your install.

---

## Environment configuration

Copy/edit repo-root `.env` (never commit it):

```powershell
Copy-Item .env.example .env
notepad .env
```

Important variables:

```env
DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5432/ai_job_agent
DATABASE_URL_SYNC=postgresql://postgres:<password>@localhost:5432/ai_job_agent
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

All hosts are **localhost / 127.0.0.1** — there are no container service names.

---

## Database setup

1. Start PostgreSQL (Windows service).
2. Create the database (pick one):

```powershell
# If createdb is on PATH:
createdb -U postgres ai_job_agent
```

```sql
-- In psql or pgAdmin
CREATE DATABASE ai_job_agent;
```

3. Enable pgvector in that database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

4. Run migrations explicitly (also done by `setup.ps1`):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

Migrations are **not** applied automatically on every API startup.

---

## Ollama setup

```powershell
ollama --version
ollama list
ollama pull llama3.2
ollama pull nomic-embed-text
```

Use the model names from your `.env` (`OLLAMA_MODEL`, `EMBEDDING_MODEL` / `OLLAMA_EMBED_MODEL`).

Verify the API:

```powershell
Invoke-WebRequest http://localhost:11434/api/tags
```

---

## Start the application

### All-in-one (recommended)

```powershell
.\scripts\check-services.ps1   # optional; PostgreSQL/Redis/Ollama should be up
.\scripts\dev.ps1
```

`dev.ps1` opens separate PowerShell windows for:

- Backend (Uvicorn)
- Celery worker (`--pool=solo`)
- Frontend (Next.js)

Then open:

- Frontend: http://localhost:3000  
- Backend: http://127.0.0.1:8000  
- Swagger: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

### Individual services

```powershell
.\scripts\start-backend.ps1
.\scripts\start-worker.ps1
.\scripts\start-frontend.ps1
```

Or manually:

```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Worker (Windows)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# Frontend
cd frontend
npm run dev
```

---

## Service status

```powershell
.\scripts\check-services.ps1
```

Example:

```text
AI Job Agent Service Status

PostgreSQL  [OK]
Redis       [OK]
Ollama      [OK]
Backend     [OK]
Frontend    [OK]
```

---

## Primary product workflow

1. Register / sign in  
2. Upload resume (PDF / DOCX / TXT)  
3. Discover Greenhouse + Lever public jobs  
4. Review ranked matches  
5. Shortlist → Prepare → Review & Apply  
6. Track status / follow-ups / analytics  

---

## LLM providers

Provider abstraction is unchanged:

- **Ollama** (default, free/local)
- Optional Gemini
- Optional OpenAI-compatible

Set `LLM_PROVIDER=ollama|gemini|openai` in `.env`.

---

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/unit -q
```

```powershell
cd frontend
npm run build
```

Playwright browser (application assistant):

```powershell
cd backend
.\.venv\Scripts\python.exe -m playwright install chromium
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `PostgreSQL unavailable` | Start the Windows PostgreSQL service; confirm `localhost:5432`; check password in `.env` |
| `Redis unavailable` | Start Redis/Memurai on `localhost:6379` |
| `Ollama unavailable` | Launch Ollama Desktop; run `ollama list` |
| Port already in use | Change `BACKEND_PORT` / stop the other process on 3000/8000 |
| venv activation blocked | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `alembic upgrade` fails | Create DB + `CREATE EXTENSION vector;` then retry |
| Playwright missing | `python -m playwright install chromium` |
| Frontend cannot reach API | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` and CORS includes your origin |
| npm install fails | Use Node 20+; delete `frontend\node_modules` and retry |
| Celery crashes on Windows | Always use `--pool=solo` (scripts already do) |

---

## Compliance

- Uses **public** Greenhouse / Lever APIs only  
- Does **not** bypass CAPTCHA, MFA, auth, robots, or anti-bot controls  
- Never fabricates candidate experience  
- Requires explicit **Review & Apply** confirmation before marking submitted  

---

## API highlights

- `GET /health`
- `POST /api/resume/upload`
- `GET /api/resume/profile`
- `POST /api/jobs/discover`
- `GET /api/jobs`
- `POST /api/jobs/{id}/shortlist`
- `POST /api/jobs/{id}/match`
- `POST /api/jobs/{id}/tailor-resume`
- `POST /api/applications/prepare`
- `POST /api/applications/{id}/submit`
- `GET /api/analytics`

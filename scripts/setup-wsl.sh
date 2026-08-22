#!/bin/bash
# Native setup inside WSL Ubuntu (no Docker).
# Prefer Python 3.12 — system Python 3.14 often lacks wheels for DB drivers.
# Note: this file must use LF line endings (not CRLF). If you see
#   env: $'bash\r': No such file or directory
# run:  sed -i 's/\r$//' scripts/setup-wsl.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Pathfind — WSL setup"
echo "Repo: $ROOT"
echo

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Missing command: $1"
    echo "       $2"
    exit 1
  fi
  echo "[OK] $1"
}

# Prefer 3.12 when available
PYTHON_BIN=""
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
else
  PYTHON_BIN="python3"
fi

echo "Using interpreter: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.major)')"
MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$MAJOR" -eq 3 && "$MINOR" -ge 14 ]]; then
  echo
  echo "[ERROR] Python $VER is too new for several pinned wheels (asyncpg/psycopg/pydantic)."
  echo "Install Python 3.12 in WSL, then re-run this script:"
  echo "  sudo apt update"
  echo "  sudo apt install -y python3.12 python3.12-venv python3.12-dev libpq-dev build-essential"
  echo "  rm -rf backend/.venv"
  echo "  ./scripts/setup-wsl.sh"
  exit 1
fi

need node "Install Node.js 20+ (e.g. nodesource or nvm)."
need npm "Install npm with Node.js."

if ! (command -v psql >/dev/null 2>&1 || timeout 1 bash -c 'echo >/dev/tcp/127.0.0.1/5432' 2>/dev/null); then
  echo "[WARN] PostgreSQL not detected on localhost:5432 — install/start it before migrations."
else
  echo "[OK] PostgreSQL port or psql"
fi

if timeout 1 bash -c 'echo >/dev/tcp/127.0.0.1/6379' 2>/dev/null; then
  echo "[OK] Redis port 6379"
else
  echo "[WARN] Redis not detected on localhost:6379"
fi

if command -v ollama >/dev/null 2>&1 || timeout 1 bash -c 'echo >/dev/tcp/127.0.0.1/11434' 2>/dev/null; then
  echo "[OK] Ollama"
else
  echo "[WARN] Ollama not detected on localhost:11434"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[OK] Created .env — edit DATABASE_URL* passwords"
else
  echo "[OK] .env exists"
fi

# Optional build deps if a package falls back to source builds
if command -v apt-get >/dev/null 2>&1; then
  if ! command -v pg_config >/dev/null 2>&1; then
    echo "Installing libpq-dev (provides pg_config) if you have sudo..."
    sudo apt-get update -y
    sudo apt-get install -y libpq-dev build-essential || true
  fi
fi

cd "$ROOT/backend"
rm -rf .venv
"$PYTHON_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
python -m playwright install chromium || echo "[WARN] Playwright browser install failed"

cd "$ROOT/frontend"
npm install

cd "$ROOT/backend"
echo "Running migrations (DB must exist: ai_job_agent + CREATE EXTENSION vector)..."
alembic upgrade head || {
  echo "[ERROR] alembic failed — create DB/extension and fix .env, then: cd backend && source .venv/bin/activate && alembic upgrade head"
  exit 1
}

echo
echo "Setup complete."
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
echo "  Worker:   cd backend && source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info"
echo "  Frontend: cd frontend && npm run dev"

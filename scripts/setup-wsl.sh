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
  echo "[ERROR] Python $VER is too new for this project (need 3.11 or 3.12)."
  echo "python3.12 was not found on PATH, so the script fell back to system python3."
  echo
  echo "Install Python 3.12, then re-run ./scripts/setup-wsl.sh"
  echo
  echo "Option A — deadsnakes PPA (recommended on newer Ubuntu):"
  echo "  sudo apt update"
  echo "  sudo apt install -y software-properties-common"
  echo "  sudo add-apt-repository -y ppa:deadsnakes/ppa"
  echo "  sudo apt update"
  echo "  sudo apt install -y python3.12 python3.12-venv python3.12-dev libpq-dev build-essential"
  echo "  rm -rf backend/.venv"
  echo "  ./scripts/setup-wsl.sh"
  echo
  echo "Option B — uv (downloads CPython 3.12 into the project):"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  source \$HOME/.local/bin/env"
  echo "  cd backend && rm -rf .venv"
  echo "  uv venv --python 3.12 .venv"
  echo "  source .venv/bin/activate"
  echo "  uv pip install -r requirements.txt"
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
if [[ -d .venv ]]; then
  echo "[OK] Reusing existing backend/.venv (delete it manually if you need a clean recreate)"
else
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
python -m playwright install chromium || echo "[WARN] Playwright browser install failed (retry later)"
if command -v sudo >/dev/null 2>&1; then
  echo "Installing Playwright OS libraries for Ubuntu 24.04+/26.04 (t64 packages)..."
  # playwright install-deps often fails on Ubuntu 26.04 (resolute) due to obsolete package names
  sudo apt-get install -y \
    libnss3 libnspr4 \
    libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 \
    libcups2t64 libdrm2 libdbus-1-3 libxcb1 libx11-6 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libxkbcommon0 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2t64 libxshmfence1 \
    fonts-liberation ca-certificates \
    || echo "[WARN] Some Playwright libs missing — browser assist may not work yet; core app still runs."
fi

cd "$ROOT/frontend"
echo "Installing frontend dependencies (npm)..."
npm config set fetch-retries 5
npm config set fetch-retry-mintimeout 20000
npm config set fetch-retry-maxtimeout 120000
npm config set fetch-timeout 300000
if ! npm install; then
  echo "[WARN] npm install failed (often network timeout). Retrying once..."
  sleep 3
  npm install || {
    echo "[ERROR] npm install failed. Retry manually:"
    echo "  cd frontend && npm install"
    exit 1
  }
fi

cd "$ROOT/backend"
echo "Running migrations (DB must exist: ai_job_agent + CREATE EXTENSION vector)..."
alembic upgrade head || {
  echo "[WARN] alembic failed — start PostgreSQL, create DB/extension, fix .env, then:"
  echo "  cd backend && source .venv/bin/activate && alembic upgrade head"
}

echo
echo "Setup complete (or as far as local services allow)."
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
echo "  Worker:   cd backend && source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info"
echo "  Frontend: cd frontend && npm run dev"
echo
echo "If Postgres/Redis/Ollama were missing, start them, then run alembic upgrade head."

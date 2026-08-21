#Requires -Version 5.1
<#
.SYNOPSIS
  One-time native Windows setup for Pathfind AI Job Agent (no Docker).
#>
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

$RepoRoot = Get-RepoRoot -ScriptDir $ScriptDir
Set-Location $RepoRoot

Write-Host ""
Write-Host "Pathfind AI Job Agent — Windows setup" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

$failed = $false

# --- Prerequisites ---
$pythonCmd = Get-PythonCommand
if ($pythonCmd) {
    $pyVer = & $pythonCmd --version 2>&1
    Write-Status -Name "Python ($pyVer)" -Ok $true
}
else {
    Write-Status -Name "Python" -Ok $false -Detail "Install Python 3.11+ from https://www.python.org/downloads/ and enable 'Add to PATH'."
    $failed = $true
}

if (Test-CommandExists "node") {
    $nodeVer = & node --version 2>&1
    Write-Status -Name "Node.js ($nodeVer)" -Ok $true
}
else {
    Write-Status -Name "Node.js" -Ok $false -Detail "Install Node.js 20+ LTS from https://nodejs.org/"
    $failed = $true
}

if (Test-CommandExists "npm") {
    Write-Status -Name "npm" -Ok $true
}
else {
    Write-Status -Name "npm" -Ok $false -Detail "npm should come with Node.js."
    $failed = $true
}

$pgOk = (Test-CommandExists "psql") -or (Test-TcpPort -HostName "127.0.0.1" -Port 5432)
if ($pgOk) {
    Write-Status -Name "PostgreSQL (port 5432 or psql)" -Ok $true
}
else {
    Write-Status -Name "PostgreSQL" -Ok $false -Detail "Install PostgreSQL for Windows and ensure it listens on localhost:5432. Also install the pgvector extension."
    $failed = $true
}

$redisOk = Test-TcpPort -HostName "127.0.0.1" -Port 6379
if ($redisOk) {
    Write-Status -Name "Redis (port 6379)" -Ok $true
}
else {
    Write-Status -Name "Redis" -Ok $false -Detail "Install Redis for Windows, Memurai, or another Redis-compatible service on localhost:6379."
    $failed = $true
}

if (Test-CommandExists "ollama") {
    Write-Status -Name "Ollama CLI" -Ok $true
}
elseif (Test-TcpPort -HostName "127.0.0.1" -Port 11434) {
    Write-Status -Name "Ollama (port 11434)" -Ok $true
}
else {
    Write-Status -Name "Ollama" -Ok $false -Detail "Install Ollama for Windows from https://ollama.com/download and start it."
    $failed = $true
}

if ($failed) {
    Write-Host ""
    Write-Host "Fix the missing prerequisites above, then re-run .\scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# --- .env ---
$envExample = Join-Path $RepoRoot ".env.example"
$envFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "[OK] Created .env from .env.example — edit DATABASE_URL password before continuing." -ForegroundColor Green
}
else {
    Write-Host "[OK] .env already exists" -ForegroundColor Green
}
Import-DotEnv -Path $envFile | Out-Null

# --- Python venv + deps ---
$backend = Join-Path $RepoRoot "backend"
Set-Location $backend
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment..."
    & $pythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status -Name "Create venv" -Ok $false -Detail "python -m venv failed"
        exit 1
    }
}
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$venvPip = Join-Path $backend ".venv\Scripts\pip.exe"
Write-Host "Installing Python dependencies..."
& $venvPip install --upgrade pip
& $venvPip install -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Status -Name "pip install" -Ok $false
    exit 1
}
Write-Status -Name "Python dependencies" -Ok $true

Write-Host "Installing Playwright Chromium..."
& $venvPython -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Playwright browser install failed — run: .\.venv\Scripts\python.exe -m playwright install chromium" -ForegroundColor Yellow
}
else {
    Write-Status -Name "Playwright Chromium" -Ok $true
}

# --- Node deps ---
$frontend = Join-Path $RepoRoot "frontend"
Set-Location $frontend
Write-Host "Installing Node dependencies..."
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Status -Name "npm install" -Ok $false
    exit 1
}
Write-Status -Name "Node dependencies" -Ok $true

# --- Database note + migrations ---
Write-Host ""
Write-Host "Database setup" -ForegroundColor Cyan
Write-Host "Ensure database exists (SQL if createdb is unavailable):"
Write-Host "  CREATE DATABASE ai_job_agent;"
Write-Host "Enable pgvector in that database:"
Write-Host "  CREATE EXTENSION IF NOT EXISTS vector;"
Write-Host ""

Set-Location $backend
Write-Host "Running Alembic migrations..."
& (Join-Path $backend ".venv\Scripts\alembic.exe") upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Status -Name "Alembic migrations" -Ok $false -Detail "Check DATABASE_URL_SYNC in .env and that ai_job_agent exists with pgvector."
    exit 1
}
Write-Status -Name "Alembic migrations" -Ok $true

# --- Ollama models ---
Write-Host ""
Write-Host "Ollama models" -ForegroundColor Cyan
$model = $env:OLLAMA_MODEL
if (-not $model) { $model = "llama3.2" }
$embed = $env:EMBEDDING_MODEL
if (-not $embed) {
    $embed = $env:OLLAMA_EMBED_MODEL
}
if (-not $embed) { $embed = "nomic-embed-text" }

if (Test-CommandExists "ollama") {
    Write-Host "Pull configured models (may take a while)..."
    ollama pull $model
    ollama pull $embed
    Write-Host "Installed models:"
    ollama list
}
else {
    Write-Host "[WARN] ollama CLI not on PATH — start Ollama Desktop and pull models from its UI, or add CLI to PATH." -ForegroundColor Yellow
}

Set-Location $RepoRoot
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next:"
Write-Host "  .\scripts\check-services.ps1"
Write-Host "  .\scripts\dev.ps1"
Write-Host ""
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://127.0.0.1:8000/docs"

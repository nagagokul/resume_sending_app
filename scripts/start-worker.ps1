#Requires -Version 5.1
<#
.SYNOPSIS
  Start Celery worker with Windows-compatible --pool=solo
#>
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

$RepoRoot = Get-RepoRoot -ScriptDir $ScriptDir
Import-DotEnv -Path (Join-Path $RepoRoot ".env") | Out-Null

$backend = Join-Path $RepoRoot "backend"
$python = Get-BackendVenvPython -RepoRoot $RepoRoot
if (-not $python) {
    Write-Host "[ERROR] Backend venv not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-TcpPort -HostName "127.0.0.1" -Port 6379)) {
    Write-Host "[ERROR] Redis not reachable at localhost:6379" -ForegroundColor Red
    exit 1
}

Set-Location $backend
Write-Host "Starting Celery worker (pool=solo for Windows)..." -ForegroundColor Cyan
& $python -m celery -A app.workers.celery_app worker --loglevel=info --pool=solo

#Requires -Version 5.1
<#
.SYNOPSIS
  Start backend, worker, and frontend as native Windows processes.
#>
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

$RepoRoot = Get-RepoRoot -ScriptDir $ScriptDir
Import-DotEnv -Path (Join-Path $RepoRoot ".env") | Out-Null

Write-Host ""
Write-Host "Pathfind — starting native development processes" -ForegroundColor Cyan
Write-Host ""

$ready = $true
if (-not (Test-TcpPort -HostName "127.0.0.1" -Port 5432)) {
    Write-Status -Name "PostgreSQL" -Ok $false -Detail "Expected localhost:5432. Start your native PostgreSQL service."
    $ready = $false
}
else {
    Write-Status -Name "PostgreSQL" -Ok $true
}

if (-not (Test-TcpPort -HostName "127.0.0.1" -Port 6379)) {
    Write-Status -Name "Redis" -Ok $false -Detail "Expected localhost:6379. Start Redis/Memurai."
    $ready = $false
}
else {
    Write-Status -Name "Redis" -Ok $true
}

if (-not (Test-TcpPort -HostName "127.0.0.1" -Port 11434)) {
    Write-Status -Name "Ollama" -Ok $false -Detail "Expected localhost:11434. Start Ollama for Windows."
    $ready = $false
}
else {
    Write-Status -Name "Ollama" -Ok $true
}

if (-not $ready) {
    Write-Host ""
    Write-Host "Start the missing external services, then re-run .\scripts\dev.ps1" -ForegroundColor Yellow
    exit 1
}

$python = Get-BackendVenvPython -RepoRoot $RepoRoot
if (-not $python) {
    Write-Host "[ERROR] Backend venv missing. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $RepoRoot "frontend\node_modules"))) {
    Write-Host "[ERROR] Frontend dependencies missing. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$logs = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$hostName = $env:BACKEND_HOST
if (-not $hostName) { $hostName = "127.0.0.1" }
$port = $env:BACKEND_PORT
if (-not $port) { $port = "8000" }
if (-not $env:NEXT_PUBLIC_API_URL) {
    $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
}

$backendDir = Join-Path $RepoRoot "backend"
$frontendDir = Join-Path $RepoRoot "frontend"

Write-Host ""
Write-Host "Launching Backend, Worker, and Frontend in separate windows..." -ForegroundColor Cyan

$backendCmd = @"
Set-Location '$backendDir'
`$env:DATABASE_URL='$($env:DATABASE_URL)'
`$env:DATABASE_URL_SYNC='$($env:DATABASE_URL_SYNC)'
`$env:REDIS_URL='$($env:REDIS_URL)'
`$env:CELERY_BROKER_URL='$($env:CELERY_BROKER_URL)'
`$env:CELERY_RESULT_BACKEND='$($env:CELERY_RESULT_BACKEND)'
`$env:OLLAMA_BASE_URL='$($env:OLLAMA_BASE_URL)'
`$env:OLLAMA_MODEL='$($env:OLLAMA_MODEL)'
`$env:CORS_ORIGINS='$($env:CORS_ORIGINS)'
`$env:JWT_SECRET='$($env:JWT_SECRET)'
& '$python' -m uvicorn app.main:app --reload --host $hostName --port $port
"@

$workerCmd = @"
Set-Location '$backendDir'
`$env:DATABASE_URL='$($env:DATABASE_URL)'
`$env:DATABASE_URL_SYNC='$($env:DATABASE_URL_SYNC)'
`$env:REDIS_URL='$($env:REDIS_URL)'
`$env:CELERY_BROKER_URL='$($env:CELERY_BROKER_URL)'
`$env:CELERY_RESULT_BACKEND='$($env:CELERY_RESULT_BACKEND)'
`$env:OLLAMA_BASE_URL='$($env:OLLAMA_BASE_URL)'
& '$python' -m celery -A app.workers.celery_app worker --loglevel=info --pool=solo
"@

$frontendCmd = @"
Set-Location '$frontendDir'
`$env:NEXT_PUBLIC_API_URL='$($env:NEXT_PUBLIC_API_URL)'
npm run dev
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd) | Out-Null
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $workerCmd) | Out-Null
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCmd) | Out-Null

Write-Host ""
Write-Host "Started:" -ForegroundColor Green
Write-Host "  Backend  http://${hostName}:${port}"
Write-Host "  Swagger  http://${hostName}:${port}/docs"
Write-Host "  Frontend http://localhost:3000"
Write-Host "  Worker   Celery (--pool=solo)"
Write-Host ""
Write-Host "Close the spawned PowerShell windows to stop each process."
Write-Host "Status check: .\scripts\check-services.ps1"

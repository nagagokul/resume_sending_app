#Requires -Version 5.1
<#
.SYNOPSIS
  Start FastAPI backend on 127.0.0.1:8000
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

$hostName = $env:BACKEND_HOST
if (-not $hostName) { $hostName = "127.0.0.1" }
$port = $env:BACKEND_PORT
if (-not $port) { $port = "8000" }

Set-Location $backend
Write-Host "Starting FastAPI on http://${hostName}:${port}" -ForegroundColor Cyan
Write-Host "Swagger: http://${hostName}:${port}/docs"
& $python -m uvicorn app.main:app --reload --host $hostName --port $port

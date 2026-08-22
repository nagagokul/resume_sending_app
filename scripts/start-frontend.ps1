#Requires -Version 5.1
<#
.SYNOPSIS
  Start Next.js frontend on localhost:3000
#>
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

$RepoRoot = Get-RepoRoot -ScriptDir $ScriptDir
Import-DotEnv -Path (Join-Path $RepoRoot ".env") | Out-Null

if (-not $env:NEXT_PUBLIC_API_URL) {
    $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
}

$frontend = Join-Path $RepoRoot "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "[ERROR] frontend/node_modules missing. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Set-Location $frontend
Write-Host "Starting Next.js on http://localhost:3000" -ForegroundColor Cyan
Write-Host "API URL: $($env:NEXT_PUBLIC_API_URL)"
npm run dev

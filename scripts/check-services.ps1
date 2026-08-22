#Requires -Version 5.1
<#
.SYNOPSIS
  Check native local services for Pathfind AI Job Agent.
#>
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

$RepoRoot = Get-RepoRoot -ScriptDir $ScriptDir
$envFile = Join-Path $RepoRoot ".env"
Import-DotEnv -Path $envFile | Out-Null

Write-Host ""
Write-Host "AI Job Agent Service Status" -ForegroundColor Cyan
Write-Host ""

function Show-Service {
    param(
        [string]$Label,
        [string]$HostName,
        [int]$Port
    )
    $ok = Test-TcpPort -HostName $HostName -Port $Port
    if ($ok) {
        Write-Host ("{0,-12} [OK]" -f $Label) -ForegroundColor Green
    }
    else {
        Write-Host ("{0,-12} [FAILED]" -f $Label) -ForegroundColor Red
        Write-Host ("Expected: {0}:{1}" -f $HostName, $Port) -ForegroundColor Yellow
    }
    return $ok
}

$allOk = $true
if (-not (Show-Service -Label "PostgreSQL" -HostName "127.0.0.1" -Port 5432)) { $allOk = $false }
if (-not (Show-Service -Label "Redis" -HostName "127.0.0.1" -Port 6379)) { $allOk = $false }
if (-not (Show-Service -Label "Ollama" -HostName "127.0.0.1" -Port 11434)) { $allOk = $false }
if (-not (Show-Service -Label "Backend" -HostName "127.0.0.1" -Port 8000)) { $allOk = $false }
if (-not (Show-Service -Label "Frontend" -HostName "127.0.0.1" -Port 3000)) { $allOk = $false }

Write-Host ""
if ($allOk) {
    Write-Host "All checked endpoints are reachable." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "One or more services are unavailable. Start missing native services, then re-check." -ForegroundColor Yellow
    Write-Host "Tip: PostgreSQL, Redis, and Ollama must be running before .\scripts\dev.ps1"
    exit 1
}

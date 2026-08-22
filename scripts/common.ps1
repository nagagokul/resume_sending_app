# Shared helpers for Pathfind AI Job Agent Windows scripts (PowerShell 5.1+)

function Get-RepoRoot {
    param([string]$ScriptDir)
    return (Resolve-Path (Join-Path $ScriptDir "..")).Path
}

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $false
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) {
            return
        }
        $name = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        Set-Item -Path "Env:$name" -Value $value
    }
    return $true
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-TcpPort {
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutMs = 1500
    )
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $ok) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar) | Out-Null
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Write-Status {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail = ""
    )
    if ($Ok) {
        Write-Host ("[{0}] {1}" -f "OK", $Name) -ForegroundColor Green
    }
    else {
        Write-Host ("[{0}] {1}" -f "ERROR", $Name) -ForegroundColor Red
        if ($Detail) {
            Write-Host "       $Detail" -ForegroundColor Yellow
        }
    }
}

function Get-PythonCommand {
    if (Test-CommandExists "python") {
        $ver = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -or "$ver" -match "Python") {
            return "python"
        }
    }
    if (Test-CommandExists "py") {
        return "py"
    }
    return $null
}

function Get-BackendVenvPython {
    param([string]$RepoRoot)
    $win = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
    if (Test-Path $win) {
        return $win
    }
    return $null
}

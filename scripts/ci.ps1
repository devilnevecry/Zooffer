# Local equivalent of the GitHub Actions CI pipeline.
#
# Usage:
#   .\scripts\ci.ps1                 # all gates
#   .\scripts\ci.ps1 -SkipTests      # skip pytest (for a quick lint/type pass)
#   .\scripts\ci.ps1 -SkipWeb       # backend and security gates only
#
# Requires PostgreSQL and Redis from compose.dev.yaml for the test gate:
#   docker compose -f compose.dev.yaml up -d

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipWeb
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment not found at .venv. Run: python -m venv .venv; .venv\Scripts\python -m pip install -e 'backend[dev]'"
}

$env:PYTHONPATH = "backend;bot"
$failures = New-Object System.Collections.Generic.List[string]
$stepNumber = 0

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Body
    )
    $script:stepNumber++
    Write-Host ""
    Write-Host "[$script:stepNumber] $Name" -ForegroundColor Cyan
    $started = Get-Date
    # Never let a previous step's native exit code decide this step's result.
    $global:LASTEXITCODE = 0
    try {
        & $Body
        if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
            throw "command exited with code $LASTEXITCODE"
        }
        $elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
        Write-Host "  PASS ($elapsed s)" -ForegroundColor Green
    }
    catch {
        $elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
        Write-Host "  FAIL: $($_.Exception.Message) ($elapsed s)" -ForegroundColor Red
        $failures.Add($Name)
    }
}

Invoke-Step "Ruff lint" {
    & $python -m ruff check backend scripts bot
}

Invoke-Step "Ruff format check" {
    & $python -m ruff format --check backend scripts bot
}

Invoke-Step "Mypy (shared backend)" {
    & $python -m mypy backend\zooffer
}

Invoke-Step "Bandit (SAST)" {
    # Bandit writes "nosec encountered" advisories to stderr even on a clean run. Start-Process
    # avoids PowerShell's native-stderr handling under $ErrorActionPreference=Stop; only the
    # process exit code and the stdout findings matter for the gate.
    $stdout = Join-Path $env:TEMP "zooffer-bandit-out.txt"
    $stderr = Join-Path $env:TEMP "zooffer-bandit-err.txt"
    $process = Start-Process -FilePath $python -NoNewWindow -Wait -PassThru `
        -ArgumentList @("-m", "bandit", "-q", "-r", "backend\zooffer", "bot\zooffer_bot", "-x", "tests", "-ll") `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Get-Content $stdout -ErrorAction SilentlyContinue | Write-Host
    if ($process.ExitCode -ne 0) {
        Get-Content $stderr -ErrorAction SilentlyContinue | Write-Host
        throw "bandit exited with code $($process.ExitCode)"
    }
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
}

if (-not $SkipTests) {
    Invoke-Step "pytest (PostgreSQL)" {
        & $python -m pytest backend\tests -q
    }
}

if (-not $SkipWeb) {
    Invoke-Step "Web type check" {
        Push-Location web
        try { npm run typecheck } finally { Pop-Location }
    }

    Invoke-Step "Web lint" {
        Push-Location web
        try { npm run lint } finally { Pop-Location }
    }

    Invoke-Step "Web format check" {
        Push-Location web
        try { npm run format:check } finally { Pop-Location }
    }

    Invoke-Step "Web production build" {
        Push-Location web
        try { npm run build } finally { Pop-Location }
    }
}

$gitleaks = Get-Command gitleaks -ErrorAction SilentlyContinue
if ($gitleaks) {
    Invoke-Step "gitleaks (secret scan)" {
        gitleaks detect --source . --redact --no-banner
    }
}
else {
    Write-Host ""
    Write-Host "SKIP gitleaks: not installed locally. CI runs it in the security job." -ForegroundColor Yellow
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "CI failed: $($failures -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "CI passed." -ForegroundColor Green

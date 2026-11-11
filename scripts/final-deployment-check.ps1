[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $repoRoot "apps\web"
$apiRoot = Join-Path $repoRoot "apps\api"
$script:Results = [System.Collections.Generic.List[object]]::new()
$script:HasCriticalBlocker = $false

function Add-CheckResult {
    param(
        [string]$Name,
        [ValidateSet("PASS", "FAIL", "BLOCKED")]
        [string]$Status,
        [string]$Detail,
        [bool]$Critical = $false
    )

    $script:Results.Add([pscustomobject]@{
        Name = $Name
        Status = $Status
        Detail = $Detail
    })
    if ($Critical -and $Status -ne "PASS") {
        $script:HasCriticalBlocker = $true
    }
}

function Invoke-FrontendCheck {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Push-Location $webRoot
    try {
        & $Command
        $exitCode = $LASTEXITCODE
    }
    catch {
        $exitCode = 1
    }
    finally {
        Pop-Location
    }

    if ($exitCode -eq 0) {
        Add-CheckResult $Name "PASS" "Command completed successfully."
    }
    else {
        Add-CheckResult $Name "FAIL" "Command failed (exit code $exitCode)." $true
    }
}

Write-Host "eCare final deployment checks"
Write-Host "Repository: $repoRoot"
Write-Host "No .env files will be read. No databases, deployments, or Git state will be changed."
Write-Host ""

$requiredVariables = @(
    "NEXT_PUBLIC_API_URL",
    "DATABASE_URL",
    "ECARE_SECRET_KEY",
    "ECARE_CORS_ORIGINS",
    "ECARE_DATABASE_ENV"
)
foreach ($name in $requiredVariables) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        Add-CheckResult "Process environment: $name" "BLOCKED" "Missing." $true
    }
    else {
        Add-CheckResult "Process environment: $name" "PASS" "Present; value suppressed."
    }
}

$postgresServices = @(
    Get-Service -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^postgresql" }
)
if ($postgresServices.Count -gt 0) {
    $runningServices = @($postgresServices | Where-Object { $_.Status -eq "Running" })
    if ($runningServices.Count -gt 0) {
        Add-CheckResult "PostgreSQL Windows service" "PASS" "A PostgreSQL service is running."
    }
    else {
        Add-CheckResult "PostgreSQL Windows service" "BLOCKED" "PostgreSQL service is installed but not running." $true
    }
}
else {
    Add-CheckResult "PostgreSQL Windows service" "BLOCKED" "No PostgreSQL Windows service was found." $false
}

$postgresAcceptingConnections = $false
try {
    $postgresAcceptingConnections = Test-NetConnection `
        -ComputerName "127.0.0.1" `
        -Port 5432 `
        -InformationLevel Quiet `
        -WarningAction SilentlyContinue `
        -ErrorAction SilentlyContinue
}
catch {
    $postgresAcceptingConnections = $false
}
if ($postgresAcceptingConnections) {
    Add-CheckResult "PostgreSQL loopback connectivity" "PASS" "127.0.0.1:5432 accepts TCP connections."
}
else {
    Add-CheckResult "PostgreSQL loopback connectivity" "BLOCKED" "127.0.0.1:5432 is not accepting TCP connections." $true
}

$pythonCandidates = @(
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    (Join-Path $apiRoot ".venv\Scripts\python.exe")
)
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonCandidates += $pythonCommand.Source
}
$pythonExe = $pythonCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1

$databaseCheckCode = @'
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "apps", "api"))
try:
    from app.database_safety import require_test_target
    from sqlalchemy import create_engine, text
    url = os.environ.get("DATABASE_URL")
    database_name = require_test_target(url, os.environ.get("ECARE_DATABASE_ENV"))
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            actual_name = connection.execute(text("SELECT current_database()")).scalar_one()
            if actual_name != database_name:
                raise RuntimeError()
    finally:
        engine.dispose()
    print("PASS")
except Exception:
    print("BLOCKED")
    sys.exit(1)
'@

$databaseConfigured = -not [string]::IsNullOrWhiteSpace(
    [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
)
$databaseEnvironment = [Environment]::GetEnvironmentVariable("ECARE_DATABASE_ENV", "Process")
if (-not $databaseConfigured -or $databaseEnvironment -ne "test") {
    Add-CheckResult "Isolated PostgreSQL test database" "BLOCKED" "A process DATABASE_URL and ECARE_DATABASE_ENV=test are required; no connection was attempted." $true
}
elseif (-not $pythonExe) {
    Add-CheckResult "Isolated PostgreSQL test database" "BLOCKED" "Python was not found; database safety and connectivity could not be verified." $true
}
else {
    Push-Location $repoRoot
    try {
        $databaseCheckOutput = & $pythonExe -c $databaseCheckCode 2>$null
        $databaseCheckExitCode = $LASTEXITCODE
    }
    catch {
        $databaseCheckOutput = "BLOCKED"
        $databaseCheckExitCode = 1
    }
    finally {
        Pop-Location
    }

    if ($databaseCheckExitCode -eq 0 -and $databaseCheckOutput -contains "PASS") {
        Add-CheckResult "Isolated PostgreSQL test database" "PASS" "The backend safety guard accepted the loopback _test target and a read-only connection succeeded."
    }
    else {
        Add-CheckResult "Isolated PostgreSQL test database" "BLOCKED" "The test-target guard or read-only connection failed; details suppressed. No migration was run." $true
    }
}

$vercelCommand = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelCommand) {
    Add-CheckResult "Vercel CLI" "BLOCKED" "Vercel CLI is not installed." $true
    Add-CheckResult "Vercel authentication" "BLOCKED" "Cannot check authentication without the CLI." $true
}
else {
    Add-CheckResult "Vercel CLI" "PASS" "Vercel CLI is installed."
    $vercelAuthOutput = & $vercelCommand.Source whoami --no-color 2>&1
    $vercelAuthExitCode = $LASTEXITCODE
    if ($vercelAuthExitCode -eq 0) {
        Add-CheckResult "Vercel authentication" "PASS" "Authenticated; account details suppressed."
    }
    else {
        Add-CheckResult "Vercel authentication" "BLOCKED" "Authentication is invalid or unavailable. Run: vercel login" $true
    }

    $webVercelLink = Join-Path $webRoot ".vercel\project.json"
    if (Test-Path -LiteralPath $webVercelLink) {
        Add-CheckResult "Vercel project link" "PASS" "A local project link exists under apps\web; identifiers suppressed."
    }
    else {
        Add-CheckResult "Vercel project link" "BLOCKED" "apps\web is not locally linked to a Vercel project. No project was created or linked." $true
    }

    if ($vercelAuthExitCode -eq 0) {
        $projectOutput = & $vercelCommand.Source project inspect ecare-healthcare --format json --cwd $webRoot --no-color 2>$null
        $projectExitCode = $LASTEXITCODE
        $projectData = $null
        if ($projectExitCode -eq 0) {
            try {
                $projectData = ($projectOutput -join [Environment]::NewLine) | ConvertFrom-Json
            }
            catch {
                $projectData = $null
            }
        }

        if ($null -ne $projectData -and $projectData.name -eq "ecare-healthcare") {
            Add-CheckResult "Existing Vercel project" "PASS" "ecare-healthcare was found; no new project was created."
            $rootDirectory = $projectData.rootDirectory
            if ($rootDirectory -eq "apps/web" -or $rootDirectory -eq "apps\web") {
                Add-CheckResult "Vercel root directory" "PASS" "The configured root directory is apps\web."
            }
            else {
                Add-CheckResult "Vercel root directory" "BLOCKED" "Could not verify apps\web as the configured root directory." $true
            }
        }
        else {
            Add-CheckResult "Existing Vercel project and root" "BLOCKED" "Project inspection failed or did not confirm ecare-healthcare; details suppressed." $true
        }
    }
    else {
        Add-CheckResult "Existing Vercel project and root" "BLOCKED" "Cannot inspect project or root directory until Vercel authentication succeeds." $true
    }
}

$backendProviderFiles = @(
    "render.yaml",
    "fly.toml",
    "railway.json",
    "railway.toml",
    "Procfile"
)
$configuredBackendFiles = @(
    $backendProviderFiles |
        ForEach-Object { Join-Path $apiRoot $_ } |
        Where-Object { Test-Path -LiteralPath $_ }
)
if ($configuredBackendFiles.Count -gt 0) {
    Add-CheckResult "Backend hosting provider" "PASS" "An existing provider configuration was found: $($configuredBackendFiles.Count) file(s)."
}
else {
    Add-CheckResult "Backend hosting provider" "BLOCKED" "No backend hosting provider is configured; Docker files are provider-neutral and do not select a host." $true
}

$apiDockerfile = Join-Path $apiRoot "Dockerfile"
if (Test-Path -LiteralPath $apiDockerfile) {
    Add-CheckResult "Provider-neutral FastAPI container" "PASS" "Local Docker configuration is present; no provider was selected."
}
else {
    Add-CheckResult "Provider-neutral FastAPI container" "BLOCKED" "No local Dockerfile is present." $false
}

if (Test-Path -LiteralPath (Join-Path $webRoot "node_modules")) {
    Invoke-FrontendCheck "Frontend lint" { npm run lint }
    Invoke-FrontendCheck "Frontend TypeScript" { npx --no-install tsc --noEmit }
    Invoke-FrontendCheck "Package booking tests" { node --test app/lib/package-booking.test.mjs }
    Invoke-FrontendCheck "Frontend production build" { npm run build }
}
else {
    Add-CheckResult "Frontend checks" "BLOCKED" "apps\web\node_modules is missing; dependencies were not installed." $true
}

Write-Host ""
Write-Host "PASS / FAIL / BLOCKED report"
foreach ($result in $script:Results) {
    Write-Host ("[{0}] {1} - {2}" -f $result.Status, $result.Name, $result.Detail)
}

Write-Host ""
Write-Host "Manual test-database creation command (run only after confirming the database is absent):"
Write-Host 'psql -h localhost -p 5432 -U <LOCAL_POSTGRES_ADMIN> -d postgres -c "CREATE DATABASE ecare_healthcare_test;"'
Write-Host ""
Write-Host "No migrations were run."

if ($script:HasCriticalBlocker) {
    exit 1
}
exit 0

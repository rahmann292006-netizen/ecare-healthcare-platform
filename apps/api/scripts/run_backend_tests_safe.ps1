param(
    [string]$DatabaseUser = 'postgres'
)

$ErrorActionPreference = 'Stop'
$apiRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = (Resolve-Path (Join-Path $apiRoot '..\..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Project virtual-environment Python was not found.'
}

# Snapshot process-only settings so this procedure restores the caller's exact
# values, including variables that were originally unset.
$environmentNames = @(
    'DATABASE_URL',
    'ECARE_DATABASE_ENV',
    'PYTHON_DOTENV_DISABLED',
    'PYTHONPATH'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

$bstr = [IntPtr]::Zero
$plainPassword = $null
$escapedPassword = $null
$reportPath = $null
$exitCode = 1

try {
    $env:ECARE_DATABASE_ENV = 'test'
    $env:PYTHON_DOTENV_DISABLED = '1'
    $env:PYTHONPATH = $apiRoot

    $securePassword = Read-Host "Password for PostgreSQL role '$DatabaseUser' (hidden input)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $escapedPassword = [Uri]::EscapeDataString($plainPassword)
    $env:DATABASE_URL = "postgresql+psycopg://${DatabaseUser}:$escapedPassword@localhost:5432/ecare_test"

    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $bstr = [IntPtr]::Zero
    $plainPassword = $null
    $escapedPassword = $null
    $securePassword.Dispose()
    $securePassword = $null

    $verifyTarget = @'
import ipaddress
import re
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from app.database_safety import require_test_target

url = os.environ.get("DATABASE_URL")

def sanitized_error(error, connection_url):
    message = str(error)
    if connection_url:
        message = message.replace(connection_url, "<DATABASE_URL redacted>")
    message = re.sub(
        r"(?i)postgres(?:ql)?(?:\+[a-z0-9_]+)?://[^\s'\"<>]+",
        "<DATABASE_URL redacted>",
        message,
    )
    message = re.sub(
        r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\b"
        r"(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
        r"\1\2<redacted>",
        message,
    )
    return " ".join(message.split())[:600] or "No error detail available."

try:
    guarded_name = require_test_target(url, os.environ.get("ECARE_DATABASE_ENV"))
    target = make_url(url)
    if (target.drivername, target.host, target.port, target.database) != (
        "postgresql+psycopg", "localhost", 5432, "ecare_test"
    ):
        raise RuntimeError("Configured URL does not match localhost:5432/ecare_test with psycopg")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            version, database, address, port = connection.exec_driver_sql(
                "SELECT version(), current_database(), inet_server_addr()::text, current_setting('port')"
            ).one()
    finally:
        engine.dispose()

    if database != "ecare_test":
        raise RuntimeError("Connected database name does not match the required test database")
    # inet_server_addr()::text may include the host prefix (for example,
    # ::1/128). ip_interface accepts both bare addresses and CIDR notation.
    if port != "5432" or not address or not ipaddress.ip_interface(address).ip.is_loopback:
        raise RuntimeError("Connected server is not on the required loopback port")
    if not version.startswith("PostgreSQL "):
        raise RuntimeError("Connected server is not PostgreSQL")

    print(
        f"Verified {version.split()[0]} {version.split()[1]}, "
        f"database={database}, loopback address, port={port}; "
        f"safety guard accepted {guarded_name}."
    )
except Exception as error:
    detail = sanitized_error(error, url)
    print(f"Target verification failed ({type(error).__name__}): {detail}; tests were not started.")
    sys.exit(1)
'@

    $verifyTarget | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw 'Connection verification failed; the backend suite was not started.'
    }

    $reportPath = Join-Path ([IO.Path]::GetTempPath()) `
        ('ecare-backend-tests-' + [Guid]::NewGuid().ToString('N') + '.xml')
    Push-Location $apiRoot
    try {
        & $python -m pytest tests\ -v "--junitxml=$reportPath"
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if (Test-Path -LiteralPath $reportPath) {
        [xml]$report = Get-Content -LiteralPath $reportPath -Raw
        $suites = @($report.SelectNodes('//testsuite'))
        $counts = @{ tests = 0; failures = 0; errors = 0; skipped = 0 }
        foreach ($suite in $suites) {
            foreach ($key in @('tests', 'failures', 'errors', 'skipped')) {
                $counts[$key] += [int]$suite.GetAttribute($key)
            }
        }
        $failed = $counts.failures + $counts.errors
        $passed = $counts.tests - $failed - $counts.skipped
        Write-Output ("Test counts: passed={0}, failed={1}, skipped={2}, blocked=0 (pytest errors included in failed: {3})" -f `
            $passed, $failed, $counts.skipped, $counts.errors)
    }
    else {
        Write-Output 'Test counts unavailable: pytest did not produce a JUnit report.'
    }
}
catch {
    Write-Error $_.Exception.Message
    if (-not $reportPath) {
        Write-Output 'Test counts: passed=0, failed=0, skipped=0; suite not started. Blocked test total is unknown because tests were not collected.'
    }
    $exitCode = 1
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plainPassword = $null
    $escapedPassword = $null
    if ($securePassword) {
        $securePassword.Dispose()
    }
    $securePassword = $null
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
    if ($reportPath -and (Test-Path -LiteralPath $reportPath)) {
        Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
    }
}

exit $exitCode

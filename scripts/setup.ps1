#Requires -Version 7.0

[CmdletBinding()]
param(
    [string]$ProjectRoot,

    [switch]$SkipFrontend,

    [switch]$SkipValidation,

    [switch]$OverwriteEnvironment
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"

Write-Host ""
Write-Host "Options Intraday Scalper local setup" -ForegroundColor Green
Write-Host "Project: $Root"

Assert-ScalperCommand -Name "docker" -InstallHint "Install and start Docker Desktop." | Out-Null
Assert-ScalperCommand -Name "uv" -InstallHint "Install uv, then open a new PowerShell 7 session." | Out-Null
if (-not $SkipFrontend) {
    Assert-ScalperCommand -Name "npm" -InstallHint "Install Node.js 22 or newer." | Out-Null
}

Write-ScalperSection "Preparing the local environment"
if ($OverwriteEnvironment -or -not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    if (-not (Test-Path -LiteralPath $EnvExample -PathType Leaf)) {
        throw "Environment template not found: $EnvExample"
    }
    Copy-Item -LiteralPath $EnvExample -Destination $EnvFile -Force
    Write-Host "    Created $EnvFile from .env.example." -ForegroundColor Green
    Write-Host "    Replace PUBLIC_API_SECRET and PUBLIC_ACCOUNT_ID before Public integration testing." -ForegroundColor Yellow
}
else {
    Write-Host "    Existing .env preserved." -ForegroundColor Green
}

Write-ScalperSection "Synchronizing local PostgreSQL credentials"
$databaseSettings = Sync-ScalperLocalDatabaseUrl -EnvFile $EnvFile
if ($databaseSettings.Changed) {
    Write-Host "    Updated DATABASE_URL to match POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB." -ForegroundColor Yellow
}
else {
    Write-Host "    DATABASE_URL already matches the Docker Compose credentials." -ForegroundColor Green
}
Write-Host "    Database: $($databaseSettings.Database)" -ForegroundColor DarkGray
Write-Host "    User:     $($databaseSettings.User)" -ForegroundColor DarkGray

Write-ScalperSection "Starting PostgreSQL"
Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "up", "-d", "postgres") -WorkingDirectory $Root
Wait-ScalperTcpPort -Name "PostgreSQL" -Port 5432 -TimeoutSeconds 90

Write-ScalperSection "Installing backend dependencies"
Invoke-ScalperNative -FilePath "uv" -ArgumentList @("sync", "--all-groups") -WorkingDirectory $Backend

Write-ScalperSection "Applying Alembic migrations"
Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "alembic", "upgrade", "head") -WorkingDirectory $Backend

if (-not $SkipFrontend) {
    Write-ScalperSection "Installing frontend dependencies"
    $lockFile = Join-Path $Frontend "package-lock.json"
    if (Test-Path -LiteralPath $lockFile -PathType Leaf) {
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("ci") -WorkingDirectory $Frontend
    }
    else {
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("install") -WorkingDirectory $Frontend
    }
}

if (-not $SkipValidation) {
    Write-ScalperSection "Running foundation validation"
    & (Join-Path $PSScriptRoot "test.ps1") `
        -ProjectRoot $Root `
        -Quick `
        -SkipFrontend:$SkipFrontend

    if (-not $?) {
        throw "Foundation validation failed."
    }
}

Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "Start development services with: .\scripts\start.ps1"

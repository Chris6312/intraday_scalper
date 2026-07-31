#Requires -Version 7.0

[CmdletBinding()]
param(
    [string]$ProjectRoot,

    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$EnvFile = Join-Path $Root ".env"
$Backend = Join-Path $Root "backend"

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile. Run .\scripts\setup.ps1 first."
}

Assert-ScalperCommand -Name "docker" -InstallHint "Install and start Docker Desktop." | Out-Null

Write-Host ""
Write-Host "Repairing local Options Intraday Scalper database configuration" -ForegroundColor Green
Write-Host "Project: $Root"

Write-ScalperSection "Synchronizing database credentials"
$databaseSettings = Sync-ScalperLocalDatabaseUrl -EnvFile $EnvFile
if ($databaseSettings.Changed) {
    Write-Host "    DATABASE_URL was corrected." -ForegroundColor Green
}
else {
    Write-Host "    DATABASE_URL was already synchronized." -ForegroundColor Green
}
Write-Host "    Database: $($databaseSettings.Database)" -ForegroundColor DarkGray
Write-Host "    User:     $($databaseSettings.User)" -ForegroundColor DarkGray
Write-Host "    Host:     $($databaseSettings.HostName):$($databaseSettings.Port)" -ForegroundColor DarkGray

Write-ScalperSection "Starting PostgreSQL"
Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "up", "-d", "postgres") -WorkingDirectory $Root
Wait-ScalperTcpPort -Name "PostgreSQL" -Port $databaseSettings.Port -TimeoutSeconds 90

if (-not $SkipMigrations) {
    Assert-ScalperCommand -Name "uv" -InstallHint "Install uv, then rerun this script." | Out-Null

    Write-ScalperSection "Applying Alembic migrations"
    try {
        Invoke-ScalperNative `
            -FilePath "uv" `
            -ArgumentList @("run", "alembic", "upgrade", "head") `
            -WorkingDirectory $Backend
    }
    catch {
        Write-Host "" 
        Write-Host "The environment values now match, but PostgreSQL still rejected the password." -ForegroundColor Red
        Write-Host "This usually means the Docker volume was initialized earlier with different credentials." -ForegroundColor Yellow
        Write-Host "Preserve the volume and reset the role password manually, or delete the volume only if no ledger data must be kept." -ForegroundColor Yellow
        throw
    }
}

Write-Host ""
Write-Host "Database configuration repaired successfully." -ForegroundColor Green

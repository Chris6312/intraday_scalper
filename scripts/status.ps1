#Requires -Version 7.0

[CmdletBinding()]
param(
    [string]$ProjectRoot,

    [int]$BackendPort = 8000,

    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$EnvFile = Join-Path $Root ".env"
$RunStateFile = Join-Path $Root ".run\session.json"

Write-Host ""
Write-Host "Options Intraday Scalper status" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host ""

Write-Host "Configuration" -ForegroundColor DarkCyan
Write-Host "  .env:              $((Test-Path -LiteralPath $EnvFile -PathType Leaf))"
Write-Host "  Execution mode:     $(Get-ScalperDotEnvValue -EnvFile $EnvFile -Name 'EXECUTION_MODE' -DefaultValue 'PAPER')"
Write-Host "  Execution broker:   $(Get-ScalperDotEnvValue -EnvFile $EnvFile -Name 'EXECUTION_BROKER' -DefaultValue 'INTERNAL_PAPER')"
Write-Host "  Market data:        $(Get-ScalperDotEnvValue -EnvFile $EnvFile -Name 'MARKET_DATA_PROVIDER' -DefaultValue 'PUBLIC')"
if (Test-Path -LiteralPath $EnvFile -PathType Leaf) {
    try {
        $expectedDatabase = Get-ScalperLocalDatabaseSettings -EnvFile $EnvFile
        $actualDatabaseUrl = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "DATABASE_URL" -DefaultValue ""
        Write-Host "  DB credentials sync: $($actualDatabaseUrl -ceq $expectedDatabase.DatabaseUrl)"
    }
    catch {
        Write-Host "  DB credentials sync: invalid ($($_.Exception.Message))" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Ports and endpoints" -ForegroundColor DarkCyan
$postgresUp = Test-ScalperTcpPort -Port 5432
$backendUp = Test-ScalperTcpPort -Port $BackendPort
$frontendUp = Test-ScalperTcpPort -Port $FrontendPort
Write-Host "  PostgreSQL :5432:   $postgresUp"
Write-Host "  Backend    :$BackendPort`:   $backendUp"
Write-Host "  Frontend   :$FrontendPort`:   $frontendUp"

if ($backendUp) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/health" -TimeoutSec 3
        Write-Host "  API health:          $($health.status)" -ForegroundColor Green
        Write-Host "  API version:         $($health.apiVersion)"
        Write-Host "  API execution mode:  $($health.executionMode)"
        Write-Host "  API market data:     $($health.marketDataProvider)"
        Write-Host "  API broker:          $($health.executionBroker)"
    }
    catch {
        Write-Host "  API health:          unreachable ($($_.Exception.Message))" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Docker Compose" -ForegroundColor DarkCyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location -LiteralPath $Root
    try {
        & docker compose ps
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "  Docker command not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Local development processes" -ForegroundColor DarkCyan
$processes = @(Get-ScalperProjectProcesses -ProjectRoot $Root)
if ($processes.Count -eq 0) {
    Write-Host "  None found." -ForegroundColor DarkGray
}
else {
    $processes |
        Select-Object ProcessId, Name, CommandLine |
        Format-Table -Wrap -AutoSize
}

if (Test-Path -LiteralPath $RunStateFile -PathType Leaf) {
    Write-Host ""
    Write-Host "Last recorded session" -ForegroundColor DarkCyan
    Get-Content -LiteralPath $RunStateFile
}

#Requires -Version 7.0

[CmdletBinding()]
param(
    [ValidateSet("Dev", "Containers")]
    [string]$Mode = "Dev",

    [string]$ProjectRoot,

    [int]$BackendPort = 8000,

    [int]$FrontendPort = 5173,

    [switch]$SkipMigrations,

    [switch]$Build,

    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$EnvFile = Join-Path $Root ".env"
$RunDirectory = Join-Path $Root ".run"
$RunStateFile = Join-Path $RunDirectory "session.json"
$HealthUri = [uri]"http://127.0.0.1:$BackendPort/api/v1/health"
$FrontendUri = [uri]"http://127.0.0.1:$FrontendPort/"

Write-Host ""
Write-Host "Starting Options Intraday Scalper" -ForegroundColor Green
Write-Host "Project: $Root"
Write-Host "Mode:    $Mode"

Assert-ScalperCommand -Name "docker" -InstallHint "Install and start Docker Desktop." | Out-Null
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile. Run .\scripts\setup.ps1 first."
}

New-Item -ItemType Directory -Path $RunDirectory -Force | Out-Null

if ($Mode -eq "Containers" -and ($BackendPort -ne 8000 -or $FrontendPort -ne 5173)) {
    throw "Container mode uses the compose.yaml ports 8000 and 5173. Use the defaults or update compose.yaml."
}
if ($Mode -eq "Dev" -and $Build) {
    Write-Host "    NOTE: -Build applies only to Containers mode and will be ignored." -ForegroundColor Yellow
}

if ($Mode -eq "Containers") {
    Write-ScalperSection "Starting PostgreSQL container"
    Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "up", "-d", "postgres") -WorkingDirectory $Root
    Wait-ScalperTcpPort -Name "PostgreSQL" -Port 5432 -TimeoutSeconds 90

    if ($Build) {
        Write-ScalperSection "Building application containers"
        Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "build", "backend", "frontend") -WorkingDirectory $Root
    }

    if (-not $SkipMigrations) {
        Write-ScalperSection "Applying database migrations in a one-shot container"
        Invoke-ScalperNative `
            -FilePath "docker" `
            -ArgumentList @("compose", "run", "--rm", "backend", "alembic", "upgrade", "head") `
            -WorkingDirectory $Root
    }

    Write-ScalperSection "Starting backend and frontend containers"
    Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "up", "-d", "backend", "frontend") -WorkingDirectory $Root
}
else {
    Assert-ScalperCommand -Name "uv" -InstallHint "Run .\scripts\setup.ps1 after installing uv." | Out-Null
    Assert-ScalperCommand -Name "npm" -InstallHint "Install Node.js 22 or newer." | Out-Null

    $BackendVenv = Join-Path $Backend ".venv"
    $FrontendModules = Join-Path $Frontend "node_modules"
    if (-not (Test-Path -LiteralPath $BackendVenv -PathType Container)) {
        throw "Backend environment not found: $BackendVenv. Run .\scripts\setup.ps1 first."
    }
    if (-not (Test-Path -LiteralPath $FrontendModules -PathType Container)) {
        throw "Frontend dependencies not found: $FrontendModules. Run .\scripts\setup.ps1 first."
    }

    Write-ScalperSection "Starting PostgreSQL container"
    Invoke-ScalperNative -FilePath "docker" -ArgumentList @("compose", "up", "-d", "postgres") -WorkingDirectory $Root
    Wait-ScalperTcpPort -Name "PostgreSQL" -Port 5432 -TimeoutSeconds 90

    if (-not $SkipMigrations) {
        Write-ScalperSection "Applying Alembic migrations"
        Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "alembic", "upgrade", "head") -WorkingDirectory $Backend
    }

    Write-ScalperSection "Opening development consoles"
    $backendCommand = "uv run uvicorn scalper.main:app --reload --host 127.0.0.1 --port $BackendPort; exit `$LASTEXITCODE"
    $frontendCommand = "npm run dev -- --host 127.0.0.1 --port $FrontendPort; exit `$LASTEXITCODE"

    Start-ScalperConsole -Title "Intraday Scalper API" -WorkingDirectory $Backend -Command $backendCommand
    Start-Sleep -Milliseconds 600
    Start-ScalperConsole -Title "Intraday Scalper Frontend" -WorkingDirectory $Frontend -Command $frontendCommand
}

Write-ScalperSection "Waiting for application readiness"
Wait-ScalperHttpEndpoint -Name "Backend API" -Uri $HealthUri -TimeoutSeconds 90
Wait-ScalperHttpEndpoint -Name "Frontend" -Uri $FrontendUri -TimeoutSeconds 90

$state = [ordered]@{
    project_root = $Root
    mode = $Mode
    started_at = (Get-Date).ToString("o")
    backend_url = $HealthUri.AbsoluteUri
    frontend_url = $FrontendUri.AbsoluteUri
}
$state | ConvertTo-Json | Set-Content -LiteralPath $RunStateFile -Encoding utf8NoBOM

if (-not $NoBrowser) {
    Start-Process $FrontendUri.AbsoluteUri | Out-Null
}

Write-Host ""
Write-Host "Options Intraday Scalper is ready." -ForegroundColor Green
Write-Host "Backend health: $HealthUri"
Write-Host "Frontend:       $FrontendUri"
Write-Host "Execution:      INTERNAL_PAPER"
Write-Host "Mode:           PAPER"

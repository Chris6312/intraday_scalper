#Requires -Version 7.0

[CmdletBinding()]
param(
    [ValidateSet("Auto", "Dev", "Containers")]
    [string]$Mode = "Auto",

    [string]$ProjectRoot,

    [switch]$RemoveContainers,

    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$RunStateFile = Join-Path $Root ".run\session.json"

Write-Host ""
Write-Host "Stopping Options Intraday Scalper" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host "Mode:    $Mode"

function Invoke-StopStep {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host "-> $Label" -ForegroundColor DarkCyan
    try {
        & $Command
    }
    catch {
        Write-Host "   Failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if ($Mode -in @("Auto", "Dev")) {
    Invoke-StopStep "Stop project development processes" {
        $processes = @(Get-ScalperProjectProcesses -ProjectRoot $Root)
        if ($processes.Count -eq 0) {
            Write-Host "   No matching FastAPI or Vite development processes found." -ForegroundColor DarkGray
        }
        else {
            $ordered = $processes | Sort-Object ProcessId -Descending
            foreach ($process in $ordered) {
                Write-Host "   Stopping PID $($process.ProcessId): $($process.Name)" -ForegroundColor DarkGray
                Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

if ($Mode -in @("Auto", "Containers")) {
    Invoke-StopStep "Stop backend and frontend containers" {
        Push-Location -LiteralPath $Root
        try {
            & docker compose stop frontend backend
            if ($LASTEXITCODE -ne 0) {
                throw "docker compose stop frontend backend returned $LASTEXITCODE"
            }
        }
        finally {
            Pop-Location
        }
    }
}

Invoke-StopStep "Stop PostgreSQL last" {
    Push-Location -LiteralPath $Root
    try {
        if ($RemoveVolumes) {
            Write-Host "   Removing containers and the PostgreSQL volume because -RemoveVolumes was supplied." -ForegroundColor Yellow
            & docker compose down --volumes --remove-orphans
        }
        elseif ($RemoveContainers) {
            & docker compose down --remove-orphans
        }
        else {
            & docker compose stop postgres
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Docker shutdown returned $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

if (Test-Path -LiteralPath $RunStateFile -PathType Leaf) {
    Remove-Item -LiteralPath $RunStateFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Options Intraday Scalper stop sequence complete." -ForegroundColor Green
if ($RemoveVolumes) {
    Write-Host "The local PostgreSQL ledger volume was deleted." -ForegroundColor Yellow
}

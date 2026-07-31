#Requires -Version 7.0

[CmdletBinding()]
param(
    [string]$ProjectRoot,

    [switch]$Quick,

    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Write-Host ""
Write-Host "Validating Options Intraday Scalper" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host "Quick:   $Quick"

Assert-ScalperCommand -Name "uv" -InstallHint "Run .\scripts\setup.ps1 after installing uv." | Out-Null

Write-ScalperSection "Checking for tracked secrets"
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
$isGitRepository = $false

if ($null -ne $gitCommand) {
    $gitRepositoryResult = @(& git -C $Root rev-parse --is-inside-work-tree 2>$null)
    $isGitRepository = (
        $LASTEXITCODE -eq 0 -and
        $gitRepositoryResult.Count -gt 0 -and
        $gitRepositoryResult[-1].Trim() -eq "true"
    )
}

if ($isGitRepository) {
    $trackedSecrets = @(& git -C $Root ls-files | Where-Object {
        $name = [System.IO.Path]::GetFileName($_)
        $isEnvironmentFile = (
            $name -eq ".env" -or
            $name -like ".env.*" -or
            $name -like "*.env"
        )
        $isExample = $name -like "*.example"
        $isEnvironmentFile -and -not $isExample
    })
    if ($trackedSecrets.Count -gt 0) {
        throw "Potential secret environment files are tracked by Git: $($trackedSecrets -join ', ')"
    }
    Write-Host "    OK: no non-example .env files are tracked." -ForegroundColor Green
}
elseif ($null -ne $gitCommand) {
    Write-Host "    SKIP: project is not a Git worktree (common after ZIP extraction)." -ForegroundColor Yellow
}
else {
    Write-Host "    SKIP: git command not found." -ForegroundColor Yellow
}

Write-ScalperSection "Running backend tests"
Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "pytest") -WorkingDirectory $Backend

if (-not $Quick) {
    Write-ScalperSection "Running backend lint and formatting checks"
    Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "ruff", "check", "src", "tests") -WorkingDirectory $Backend
    Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "ruff", "format", "--check", "src", "tests") -WorkingDirectory $Backend

    Write-ScalperSection "Running backend type checks"
    Invoke-ScalperNative -FilePath "uv" -ArgumentList @("run", "mypy", "src") -WorkingDirectory $Backend
}

if (-not $SkipFrontend) {
    Assert-ScalperCommand -Name "npm" -InstallHint "Install Node.js 22 or newer." | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $Frontend "node_modules") -PathType Container)) {
        throw "Frontend dependencies are missing. Run .\scripts\setup.ps1 first."
    }

    Write-ScalperSection "Running frontend tests"
    Invoke-ScalperNative -FilePath "npm" -ArgumentList @("test", "--", "--run") -WorkingDirectory $Frontend

    if (-not $Quick) {
        Write-ScalperSection "Running frontend lint, type, format, and build checks"
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("run", "lint") -WorkingDirectory $Frontend
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("run", "typecheck") -WorkingDirectory $Frontend
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("run", "format:check") -WorkingDirectory $Frontend
        Invoke-ScalperNative -FilePath "npm" -ArgumentList @("run", "build") -WorkingDirectory $Frontend
    }
}

Write-Host ""
Write-Host "All requested validation checks passed." -ForegroundColor Green

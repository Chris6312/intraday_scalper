#Requires -Version 7.0

[CmdletBinding()]
param(
    [string]$ProjectRoot,

    [string]$BackupDirectory,

    [ValidateRange(1, 1000)]
    [int]$KeepLast = 10,

    [switch]$IncludeDatabase
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $BackupDirectory = Join-Path $Root "backups"
}

$BackupRoot = [System.IO.Path]::GetFullPath($BackupDirectory)
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BaseName = "options-intraday-scalper-backup-$Timestamp"
$ZipPath = Join-Path $BackupRoot "$BaseName.zip"
$ChecksumPath = "$ZipPath.sha256"
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) $BaseName
$StagingRoot = Join-Path $TempRoot "intraday_scalper"

$ExcludedFolders = @(
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".vite",
    ".vs",
    ".run",
    "backups"
)

$ExcludedFileNames = @(
    ".env",
    ".coverage"
)

$ExcludedPatterns = @(
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp"
)

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
if (Test-Path -LiteralPath $TempRoot) {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null

Write-Host ""
Write-Host "Creating Options Intraday Scalper backup" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host "Output:  $ZipPath"
Write-Host "Database dump: $IncludeDatabase"
Write-Host ""

try {
    $files = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Force | Where-Object {
        $relative = [System.IO.Path]::GetRelativePath($Root, $_.FullName)
        $parts = $relative -split "[\\/]"

        foreach ($folder in $ExcludedFolders) {
            if ($parts -contains $folder) {
                return $false
            }
        }

        if ($ExcludedFileNames -contains $_.Name) {
            return $false
        }

        foreach ($pattern in $ExcludedPatterns) {
            if ($_.Name -like $pattern) {
                return $false
            }
        }

        return $true
    })

    if ($files.Count -eq 0) {
        throw "No project files were selected for backup."
    }

    $index = 0
    foreach ($file in $files) {
        $index++
        $relative = [System.IO.Path]::GetRelativePath($Root, $file.FullName)
        $destination = Join-Path $StagingRoot $relative
        $destinationFolder = Split-Path -Parent $destination

        Write-Progress `
            -Activity "Copying project files" `
            -Status $relative `
            -PercentComplete (($index / $files.Count) * 100)

        New-Item -ItemType Directory -Path $destinationFolder -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
    Write-Progress -Activity "Copying project files" -Completed

    $databaseIncluded = $false
    if ($IncludeDatabase) {
        Write-ScalperSection "Exporting PostgreSQL ledger"
        Assert-ScalperCommand -Name "docker" -InstallHint "Docker is required for -IncludeDatabase." | Out-Null

        Push-Location -LiteralPath $Root
        try {
            $containerId = (& docker compose ps -q postgres 2>$null | Select-Object -First 1)
            if ([string]::IsNullOrWhiteSpace($containerId)) {
                throw "PostgreSQL container is not running. Start it before using -IncludeDatabase."
            }

            $EnvFile = Join-Path $Root ".env"
            $database = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "POSTGRES_DB" -DefaultValue "options_scalper"
            $user = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "POSTGRES_USER" -DefaultValue "scalper"
            $dumpPath = Join-Path $StagingRoot "database\options_scalper.sql"
            New-Item -ItemType Directory -Path (Split-Path -Parent $dumpPath) -Force | Out-Null

            $dumpProcess = Start-Process `
                -FilePath "docker" `
                -ArgumentList @(
                    "compose", "exec", "-T", "postgres", "pg_dump",
                    "--username", $user,
                    "--dbname", $database,
                    "--clean",
                    "--if-exists",
                    "--no-owner",
                    "--no-privileges"
                ) `
                -RedirectStandardOutput $dumpPath `
                -Wait `
                -PassThru `
                -NoNewWindow

            if ($dumpProcess.ExitCode -ne 0) {
                throw "pg_dump failed with exit code $($dumpProcess.ExitCode)."
            }

            $databaseIncluded = $true
            Write-Host "    Database dump added." -ForegroundColor Green
        }
        finally {
            Pop-Location
        }
    }

    $gitCommit = $null
    $gitBranch = $null
    $gitDirty = $null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Push-Location -LiteralPath $Root
        try {
            $gitCommit = (& git rev-parse HEAD 2>$null)
            $gitBranch = (& git branch --show-current 2>$null)
            $gitDirty = [bool](& git status --porcelain 2>$null)
        }
        finally {
            Pop-Location
        }
    }

    $manifest = [ordered]@{
        created_at = (Get-Date).ToString("o")
        source_root = $Root
        file_count = $files.Count
        database_included = $databaseIncluded
        secrets_included = $false
        git_commit = $gitCommit
        git_branch = $gitBranch
        git_worktree_dirty = $gitDirty
        restore_note = "Extract the intraday_scalper folder. Restore database/options_scalper.sql manually only when intentionally replacing a local ledger."
    }
    $manifest | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $StagingRoot "BACKUP_MANIFEST.json") -Encoding utf8NoBOM

    Write-ScalperSection "Compressing backup"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $TempRoot,
        $ZipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    $hash = Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256
    "$($hash.Hash.ToLowerInvariant())  $([System.IO.Path]::GetFileName($ZipPath))" |
        Set-Content -LiteralPath $ChecksumPath -Encoding ascii

    Write-ScalperSection "Pruning old backups"
    $oldBackups = @(Get-ChildItem -LiteralPath $BackupRoot -Filter "options-intraday-scalper-backup-*.zip" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $KeepLast)

    foreach ($oldBackup in $oldBackups) {
        Remove-Item -LiteralPath $oldBackup.FullName -Force
        $oldChecksum = "$($oldBackup.FullName).sha256"
        if (Test-Path -LiteralPath $oldChecksum -PathType Leaf) {
            Remove-Item -LiteralPath $oldChecksum -Force
        }
    }

    Write-Host ""
    Write-Host "Backup created successfully." -ForegroundColor Green
    Write-Host "Archive:  $ZipPath"
    Write-Host "Checksum: $ChecksumPath"
    Write-Host "Files:    $($files.Count)"
    Write-Host "Kept:     latest $KeepLast backup archives"
}
finally {
    Write-Progress -Activity "Copying project files" -Completed
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}

#Requires -Version 7.0

$script:ScalperScriptsDirectory = $PSScriptRoot
$script:DefaultScalperProjectRoot = Split-Path -Parent $script:ScalperScriptsDirectory

function Resolve-ScalperProjectRoot {
    [CmdletBinding()]
    param(
        [string]$ProjectRoot
    )

    if (-not [string]::IsNullOrWhiteSpace($ProjectRoot)) {
        $candidate = $ProjectRoot
    }
    elseif (-not [string]::IsNullOrWhiteSpace($env:INTRADAY_SCALPER_ROOT)) {
        $candidate = $env:INTRADAY_SCALPER_ROOT
    }
    else {
        $candidate = $script:DefaultScalperProjectRoot
    }

    if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
        throw "Project root does not exist: $candidate"
    }

    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $required = @(
        "compose.yaml",
        "backend\pyproject.toml",
        "frontend\package.json"
    )

    foreach ($relativePath in $required) {
        $fullPath = Join-Path $resolved $relativePath
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            throw "The folder is not an Options Intraday Scalper project. Missing: $fullPath"
        }
    }

    return $resolved
}

function Write-ScalperSection {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-ScalperCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        $message = "Required command was not found: $Name"
        if (-not [string]::IsNullOrWhiteSpace($InstallHint)) {
            $message = "$message`n$InstallHint"
        }
        throw $message
    }

    return $command
}

function Invoke-ScalperNative {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [string[]]$ArgumentList = @(),

        [string]$WorkingDirectory
    )

    $display = @($FilePath) + $ArgumentList
    Write-Host "    $($display -join ' ')" -ForegroundColor DarkGray

    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        Push-Location -LiteralPath $WorkingDirectory
    }

    try {
        & $FilePath @ArgumentList
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Command failed with exit code ${exitCode}: $($display -join ' ')"
        }
    }
    finally {
        if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
            Pop-Location
        }
    }
}

function Test-ScalperTcpPort {
    [CmdletBinding()]
    param(
        [string]$HostName = "127.0.0.1",

        [Parameter(Mandatory)]
        [int]$Port,

        [int]$ConnectTimeoutMilliseconds = 500
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        return $task.Wait($ConnectTimeoutMilliseconds) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ScalperTcpPort {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [string]$HostName = "127.0.0.1",

        [Parameter(Mandatory)]
        [int]$Port,

        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-ScalperTcpPort -HostName $HostName -Port $Port) {
            Write-Host "    OK: $Name is accepting connections on $HostName`:$Port." -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 750
    }

    throw "$Name did not become ready on $HostName`:$Port within $TimeoutSeconds seconds."
}

function Wait-ScalperHttpEndpoint {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [uri]$Uri,

        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -Method Get -TimeoutSec 3 -SkipHttpErrorCheck
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Host "    OK: $Name responded at $Uri." -ForegroundColor Green
                return
            }
        }
        catch {
            # Service may still be starting.
        }
        Start-Sleep -Milliseconds 750
    }

    throw "$Name did not become ready at $Uri within $TimeoutSeconds seconds."
}

function Get-ScalperDotEnvValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$EnvFile,

        [Parameter(Mandatory)]
        [string]$Name,

        [string]$DefaultValue
    )

    if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
        return $DefaultValue
    }

    $escapedName = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $EnvFile |
        Where-Object { $_ -match "^\s*$escapedName\s*=" } |
        Select-Object -Last 1

    if ($null -eq $line) {
        return $DefaultValue
    }

    $value = ($line -split "=", 2)[1].Trim()
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    return $value
}


function Set-ScalperDotEnvValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$EnvFile,

        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Value
    )

    $parent = Split-Path -Parent $EnvFile
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $EnvFile -PathType Leaf) {
        foreach ($line in Get-Content -LiteralPath $EnvFile) {
            $lines.Add($line)
        }
    }

    $escapedName = [regex]::Escape($Name)
    $pattern = "^\s*$escapedName\s*="
    $matchingIndexes = [System.Collections.Generic.List[int]]::new()

    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            $matchingIndexes.Add($index)
        }
    }

    $replacement = "$Name=$Value"
    if ($matchingIndexes.Count -eq 0) {
        if ($lines.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
            $lines.Add("")
        }
        $lines.Add($replacement)
    }
    else {
        $lastIndex = $matchingIndexes[$matchingIndexes.Count - 1]
        $lines[$lastIndex] = $replacement

        for ($matchIndex = $matchingIndexes.Count - 2; $matchIndex -ge 0; $matchIndex--) {
            $lines.RemoveAt($matchingIndexes[$matchIndex])
        }
    }

    [System.IO.File]::WriteAllLines(
        $EnvFile,
        $lines,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-ScalperLocalDatabaseSettings {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$EnvFile,

        [string]$HostName = "127.0.0.1",

        [ValidateRange(1, 65535)]
        [int]$Port = 5432
    )

    $database = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "POSTGRES_DB" -DefaultValue "options_scalper"
    $user = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "POSTGRES_USER" -DefaultValue "scalper"
    $password = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "POSTGRES_PASSWORD" -DefaultValue "scalper"

    if ([string]::IsNullOrWhiteSpace($database)) {
        throw "POSTGRES_DB cannot be empty in $EnvFile."
    }
    if ([string]::IsNullOrWhiteSpace($user)) {
        throw "POSTGRES_USER cannot be empty in $EnvFile."
    }
    if ([string]::IsNullOrWhiteSpace($password)) {
        throw "POSTGRES_PASSWORD cannot be empty in $EnvFile."
    }

    $encodedDatabase = [uri]::EscapeDataString($database)
    $encodedUser = [uri]::EscapeDataString($user)
    $encodedPassword = [uri]::EscapeDataString($password)
    $databaseUrl = "postgresql+asyncpg://${encodedUser}:${encodedPassword}@${HostName}:${Port}/${encodedDatabase}"

    return [pscustomobject]@{
        Database = $database
        User = $user
        Password = $password
        HostName = $HostName
        Port = $Port
        DatabaseUrl = $databaseUrl
    }
}

function Sync-ScalperLocalDatabaseUrl {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$EnvFile,

        [string]$HostName = "127.0.0.1",

        [ValidateRange(1, 65535)]
        [int]$Port = 5432
    )

    $settings = Get-ScalperLocalDatabaseSettings `
        -EnvFile $EnvFile `
        -HostName $HostName `
        -Port $Port

    $currentUrl = Get-ScalperDotEnvValue -EnvFile $EnvFile -Name "DATABASE_URL" -DefaultValue ""
    $changed = $currentUrl -cne $settings.DatabaseUrl

    if ($changed) {
        Set-ScalperDotEnvValue `
            -EnvFile $EnvFile `
            -Name "DATABASE_URL" `
            -Value $settings.DatabaseUrl
    }

    return [pscustomobject]@{
        Changed = $changed
        Database = $settings.Database
        User = $settings.User
        HostName = $settings.HostName
        Port = $settings.Port
        DatabaseUrl = $settings.DatabaseUrl
    }
}

function Start-ScalperConsole {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Title,

        [Parameter(Mandatory)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory)]
        [string]$Command
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    $pwshPath = (Get-Process -Id $PID).Path
    $windowsTerminal = Get-Command wt.exe -ErrorAction SilentlyContinue

    if ($null -ne $windowsTerminal) {
        & $windowsTerminal.Source -w 0 new-tab `
            --title $Title `
            --startingDirectory $WorkingDirectory `
            $pwshPath -NoLogo -NoProfile -NoExit -EncodedCommand $encoded

        if ($LASTEXITCODE -eq 0) {
            return
        }

        Write-Host "    Windows Terminal tab launch failed; using a separate PowerShell window." -ForegroundColor Yellow
    }

    Start-Process `
        -FilePath $pwshPath `
        -WorkingDirectory $WorkingDirectory `
        -ArgumentList @("-NoLogo", "-NoProfile", "-NoExit", "-EncodedCommand", $encoded) |
        Out-Null
}

function Get-ScalperProjectProcesses {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot
    )

    $escapedRoot = [regex]::Escape($ProjectRoot)
    $patterns = @(
        "scalper\.main:app",
        "uvicorn",
        "npm(\.cmd)?\s+run\s+dev",
        "node_modules[\\/]vite"
    )

    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = $_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) {
                return $false
            }
            if ($_.ProcessId -eq $PID) {
                return $false
            }
            if ($commandLine -notmatch $escapedRoot) {
                return $false
            }

            foreach ($pattern in $patterns) {
                if ($commandLine -match $pattern) {
                    return $true
                }
            }
            return $false
        }
}

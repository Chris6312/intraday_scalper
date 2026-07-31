#Requires -Version 7.0

[CmdletBinding()]
param(
    [ValidateSet("all", "postgres", "backend", "frontend")]
    [string]$Service = "all",

    [string]$ProjectRoot,

    [ValidateRange(1, 10000)]
    [int]$Tail = 200,

    [switch]$NoFollow
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$Root = Resolve-ScalperProjectRoot -ProjectRoot $ProjectRoot
Assert-ScalperCommand -Name "docker" -InstallHint "Install and start Docker Desktop." | Out-Null

$arguments = @("compose", "logs", "--tail", $Tail.ToString())
if (-not $NoFollow) {
    $arguments += "--follow"
}
if ($Service -ne "all") {
    $arguments += $Service
}

Write-Host ""
Write-Host "Showing Docker logs. Press Ctrl+C to stop following." -ForegroundColor Cyan
Invoke-ScalperNative -FilePath "docker" -ArgumentList $arguments -WorkingDirectory $Root

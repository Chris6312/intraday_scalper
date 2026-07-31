# Options Intraday Scalper — PowerShell 7 Toolkit

Copy the `scripts` folder into:

```text
C:\dev\intraday_scalper\scripts
```

The scripts automatically use the parent folder as the project root. You can also set:

```powershell
$env:INTRADAY_SCALPER_ROOT = "C:\dev\intraday_scalper"
```

## Initial setup

```powershell
Set-Location C:\dev\intraday_scalper
.\scripts\setup.ps1
```

## Start in development mode

PostgreSQL runs in Docker. FastAPI and Vite run in separate PowerShell 7 / Windows Terminal consoles.

```powershell
.\scripts\start.ps1
```

## Start entirely in Docker

```powershell
.\scripts\start.ps1 -Mode Containers -Build
```

## Stop

```powershell
.\scripts\stop.ps1
```

Stop and remove containers, while preserving the PostgreSQL volume:

```powershell
.\scripts\stop.ps1 -RemoveContainers
```

Delete the local PostgreSQL ledger volume only when intentionally resetting all local data:

```powershell
.\scripts\stop.ps1 -RemoveVolumes
```

## Status

```powershell
.\scripts\status.ps1
```

## Tests

Quick tests:

```powershell
.\scripts\test.ps1 -Quick
```

Full backend and frontend quality gate:

```powershell
.\scripts\test.ps1
```

## Migrations

```powershell
.\scripts\migrate.ps1
```

For a container-only environment:

```powershell
.\scripts\migrate.ps1 -Containers
```

## Backup

Source backup without local secrets, dependencies, caches, build output, or Git internals:

```powershell
.\scripts\backup.ps1
```

Include a plain-SQL PostgreSQL ledger dump when the database container is running:

```powershell
.\scripts\backup.ps1 -IncludeDatabase
```

Backups are written to `C:\dev\intraday_scalper\backups` and include a SHA-256 checksum.

## Docker logs

```powershell
.\scripts\logs.ps1
.\scripts\logs.ps1 -Service backend
.\scripts\logs.ps1 -Service postgres -NoFollow
```

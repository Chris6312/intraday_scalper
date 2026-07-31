$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Replace the Public credential placeholders locally."
}

Write-Host "Starting PostgreSQL..."
docker compose up -d postgres

Write-Host "Installing backend dependencies and applying migrations..."
Push-Location backend
uv sync --all-groups
uv run alembic upgrade head
Pop-Location

Write-Host "Installing frontend dependencies..."
Push-Location frontend
npm install
Pop-Location

Write-Host "Running Phase 0 verification..."
python scripts/verify_phase0.py

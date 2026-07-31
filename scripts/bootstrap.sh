#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Replace Public credential placeholders locally."
fi

docker compose up -d postgres
(
  cd backend
  uv sync --all-groups
  uv run alembic upgrade head
)
(
  cd frontend
  npm install
)
python scripts/verify_phase0.py

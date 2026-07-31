.PHONY: help backend-install backend-test backend-lint backend-typecheck frontend-install frontend-test frontend-lint db-up db-down migrate phase0-verify

help:
	@echo "Targets: backend-install backend-test backend-lint backend-typecheck frontend-install frontend-test frontend-lint db-up db-down migrate phase0-verify"

backend-install:
	cd backend && uv sync --all-groups

backend-test:
	cd backend && uv run pytest

backend-lint:
	cd backend && uv run ruff check src tests
	cd backend && uv run ruff format --check src tests

backend-typecheck:
	cd backend && uv run mypy src

frontend-install:
	cd frontend && npm install

frontend-test:
	cd frontend && npm test -- --run

frontend-lint:
	cd frontend && npm run lint
	cd frontend && npm run typecheck

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

phase0-verify:
	python scripts/verify_phase0.py

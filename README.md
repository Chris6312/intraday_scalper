# Options Intraday Scalper

Broker-neutral five-minute options scalping application. Version 1 is **paper trading only**.

- Market data: Public
- Execution: Internal Paper Broker
- Ledger: PostgreSQL
- Backend: Python / FastAPI
- Frontend: React / TypeScript
- Future execution: Webull after API approval and shadow validation

The complete approved product specification is in [`docs/approved-specification.md`](docs/approved-specification.md). Implementation progress is tracked in [`PHASE_CHECKLIST.md`](PHASE_CHECKLIST.md).

## Phase 0 status

The repository foundation, architecture contracts, default configuration, test scaffolding, migrations, structured logging, API versioning, and recovery/idempotency policies are present. External credentials and a live local PostgreSQL verification remain operator actions.

## Local setup

### Prerequisites

- Python 3.12 or 3.13
- `uv`
- Node.js 22+
- Docker Desktop or another Docker-compatible runtime

### Configure

```bash
cp .env.example .env
```

Replace only local secret placeholders in `.env`. Never commit `.env`.

### Start PostgreSQL and migrate

```bash
docker compose up -d postgres
cd backend
uv sync --all-groups
uv run alembic upgrade head
```

### Run backend

```bash
cd backend
uv run uvicorn scalper.main:app --reload
```

### Run frontend

```bash
cd frontend
npm install
npm run dev
```

### Verify Phase 0

```bash
python scripts/verify_phase0.py
```

On Windows PowerShell, run `scripts/bootstrap.ps1` for the initial local setup.

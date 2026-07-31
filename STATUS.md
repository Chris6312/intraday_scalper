# Project Status

## Current phase

**Phase 0 — Pre-Implementation Decisions and Foundation: in progress**

## Completed in this scaffold

- Backend and frontend project structures
- Environment templates without real credentials
- Python lint, format, type-check, and test configuration
- React/TypeScript lint, format, type-check, and test configuration
- Alembic migration tooling and baseline metadata migration
- JSON structured logging convention
- UTC storage and America/New_York display convention
- Shared domain enums
- Versioned `/api/v1` contract and OpenAPI source document
- Broker-neutral `MarketDataProvider` and `ExecutionBroker` protocols
- Canonical market-data, order, fill, position, account, and cash-event models
- Idempotency-key policy and startup-recovery plan
- Conservative simulation defaults
- Local Docker Compose topology
- CI workflow

## Remaining external actions before Phase 0 gate closes

1. Generate a Public secret key and identify the Public account ID, then place both only in local secret storage.
2. Run PostgreSQL locally and execute `alembic upgrade head`.
3. Install frontend dependencies and run frontend lint, type-check, and tests.
4. Review and approve the working defaults in `docs/decisions/ADR-0002-paper-simulation-defaults.md`.
5. Confirm the deployment host/provider for staging and production; container deployment is selected, but the vendor is intentionally unset.

No Alpaca adapter is enabled. No Webull execution code is enabled.

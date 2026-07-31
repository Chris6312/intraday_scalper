# ADR-0003: Time and Deployment Environments

- **Status:** Accepted
- **Date:** 2026-07-29

## Time

- Persist timestamps as timezone-aware UTC.
- Display and evaluate the trading schedule in `America/New_York`.
- Never store naive datetimes.
- Include the source timestamp and receive timestamp for market data.
- Use an exchange-calendar service in Phase 1 for holidays, half-days, and daylight-saving transitions.

## Environments

- `local`: Docker Compose for PostgreSQL; backend and frontend may run on the host for hot reload.
- `staging`: containerized deployment, paper mode only, isolated database and secrets.
- `production`: containerized deployment, paper mode only through Version 1; vendor intentionally undecided.

No environment may infer live execution from its name. `EXECUTION_MODE=PAPER` is independently enforced.

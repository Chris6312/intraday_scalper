# ADR-0001: Broker-Neutral Boundaries

- **Status:** Accepted for Version 1
- **Date:** 2026-07-29

## Decision

The strategy engine depends only on canonical domain models and two ports:

- `MarketDataProvider`
- `ExecutionBroker`

Public-specific code is confined to `scalper.adapters.market_data.public`. Internal paper execution is confined to `scalper.adapters.execution.internal_paper`. Strategy, indicators, contract selection, risk, positions, and performance services may not import provider or broker adapter modules.

## Version 1 bindings

- Market data provider: `PUBLIC`
- Execution broker: `INTERNAL_PAPER`
- Execution mode: `PAPER`
- Ledger: PostgreSQL

## Future bindings

Alpaca comparison remains disabled and optional. Webull is a future adapter and cannot be enabled until paper validation, API approval, shadow mode, and explicit live-mode safeguards are complete.

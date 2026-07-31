# ADR-0005: External Integration Timing

- **Status:** Accepted
- **Date:** 2026-07-29

## Public

Public is the Version 1 market-data source only. Credentials are supplied through secret storage. No Public account balances, orders, fills, positions, or P&L are authoritative for the internal paper account.

## Alpaca

Comparison mode is disabled by default. It is optional after the internal paper release has passed fill and P&L validation.

## Webull

Webull work begins only after:

1. Version 1 paper operation is stable.
2. Fill, slippage, stops, scale-outs, and P&L reconciliation pass Phase 4.
3. API access is approved and credentials are stored securely.
4. A broker adapter passes contract tests.
5. Shadow mode and order previews show acceptable agreement.
6. The user explicitly enables each later execution phase.

Live execution is outside the Version 1 release boundary.

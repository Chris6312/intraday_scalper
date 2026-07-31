# ADR-0004: Idempotency and Startup Recovery

- **Status:** Accepted
- **Date:** 2026-07-29

## Idempotency

- Every order command carries an `idempotency_key` unique within a ledger session.
- Every order event has an immutable event ID and a unique `(session_id, event_id)` constraint.
- Every fill is unique by `(execution_broker, external_fill_id)` or by a deterministic internal-paper fill ID.
- Every cash event has an immutable ID and idempotency key.
- Duplicate inputs return the original result and never create a second reservation, fill, or cash movement.

## Startup recovery order

1. Refuse startup if execution mode is not `PAPER` in Version 1.
2. Acquire a PostgreSQL advisory lock for the active ledger session.
3. Rebuild cash, reservations, positions, realized P&L, and open orders from immutable events.
4. Compare derived state with snapshots; snapshots are caches, not authority.
5. Mark quotes stale until fresh Public timestamps arrive.
6. Restore management of open positions and protective exits.
7. Cancel orphaned pending entries whose setup context cannot be recovered safely.
8. Reapply circuit breakers and the 3:30 PM ET force-flat state.
9. Emit a structured recovery report before enabling new entries.

Recovery is fail-closed: inconsistencies disable new entries and require an operator-visible audit event.

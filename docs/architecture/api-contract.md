# Backend–Frontend API Contract

The public application API is versioned under `/api/v1`.

## Rules

- Breaking changes require `/api/v2` or an explicitly versioned schema transition.
- JSON fields use `camelCase` at the HTTP boundary and `snake_case` internally.
- Money and prices are serialized as decimal strings, never binary floating-point values.
- Timestamps are RFC 3339 UTC strings.
- Every state-changing request will carry an idempotency key in Phase 1.
- WebSocket payloads use the same versioned schemas as REST resources.
- Provider-specific fields stay in adapter metadata and do not leak into strategy contracts.

The source contract is [`../../shared/openapi/options-scalper-v1.yaml`](../../shared/openapi/options-scalper-v1.yaml).

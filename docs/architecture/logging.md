# Structured Logging Convention

Backend logs are one JSON object per line.

Required fields:

- `timestamp`
- `level`
- `logger`
- `event`
- `message`
- `environment`
- `execution_mode`
- `correlation_id` when available
- `ledger_session_id` when available
- `symbol`, `order_id`, `position_id`, or `trade_id` when relevant

Secrets, access tokens, complete authorization headers, and credential values must never be logged.

Every automated decision should log both the result and a stable reason code. Human-readable text supplements reason codes but does not replace them.

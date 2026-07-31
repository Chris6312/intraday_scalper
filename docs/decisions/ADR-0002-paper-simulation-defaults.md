# ADR-0002: Paper-Simulation Working Defaults

- **Status:** Proposed working defaults; environment-configurable
- **Date:** 2026-07-29

These defaults are intentionally conservative and are not claims about any broker's actual fee schedule or fill quality.

| Setting | Working default | Rationale |
|---|---:|---|
| Starting paper balance | $25,000.00 | Useful benchmark account while remaining configurable |
| Strategy buying-power ceiling | 50% | Approved portfolio-wide ceiling |
| Commission | $0.65 per contract per side | Conservative validation assumption |
| Regulatory fee | $0.03 per contract on sells | Configurable placeholder separated from commission |
| Entry slippage | 1 valid option tick | Avoid optimistic midpoint assumptions |
| Normal-exit slippage | 1 valid option tick | Conservative liquidation estimate |
| Stop slippage | 2 valid option ticks | Allows worse stop execution in fast markets |
| Missing displayed size | At most 1 contract per unique quote event | Never assumes unlimited liquidity |
| Missing-size refill delay | 250 ms | Prevents repeated fills against one unchanged quote |
| Underlying quote stale threshold | 5 seconds | Approved initial recommendation |
| Option quote stale threshold | 3 seconds | Approved initial recommendation |
| Completed-candle grace | 2 seconds | Allows late final-bar delivery without using incomplete bars |

## Tick handling

Slippage is expressed in ticks, not a fixed dollar amount. The option-quote adapter will provide or infer the valid tick size. No simulated fill may cross beyond the order algorithm's maximum permitted price.

## Approval note

Changing these defaults affects future sessions only. Historical ledger sessions retain the configuration snapshot used when they were created.

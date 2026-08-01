# Options Intraday Scalper — Phase Checklist

Implementation checklist derived from the approved **5-Minute Options Scalper Bot** specification.

> **Release boundary:** Version 1 is paper trading only. Public supplies market data; the internal paper broker and PostgreSQL ledger remain the source of truth for account state, orders, fills, positions, and P&L.

---

## Checklist Legend

- [ ] Not started
- [x] Completed
- [ ] **Gate:** Must be completed before advancing to the next phase
- **Optional:** May be skipped without blocking the initial paper-trading release

---

## Project-Wide Non-Negotiable Requirements

- [ ] Keep strategy logic broker-neutral.
- [ ] Use Public only for market data.
- [ ] Use the internal paper broker as the Version 1 execution venue.
- [ ] Use PostgreSQL as the authoritative ledger.
- [ ] Restrict Version 1 to paper mode.
- [ ] Enforce the portfolio-wide 50% buying-power ceiling.
- [ ] Enforce the 3:30 PM ET force-flat rule.
- [ ] Make the emergency kill switch available from every primary page.
- [ ] Prevent order, fill, stop, and P&L processing from stale quotes.
- [ ] Preserve a complete audit trail for every automated decision.
- [ ] Keep credentials and secret keys out of source control.

---

# Phase 0 — Pre-Implementation Decisions and Foundation

> **Status as of 2026-07-30:** Phase 0 foundation is complete. The local runtime, PostgreSQL migration, backend and frontend validation, GitHub Actions CI, repository initialization, secret protection, and line-ending standards have been verified. Public API credentials and live Public connectivity remain Phase 1 operator tasks.

## 0.1 Resolve Configurable Values

- [x] Set the initial paper-account balance.
- [x] Define the simulated commission schedule.
- [x] Define simulated regulatory fees.
- [x] Define default option-entry and stop slippage.
- [x] Define conservative fill behavior when displayed option size is unavailable.
- [x] Set the underlying quote stale threshold; initial recommendation: 5 seconds.
- [x] Set the option quote stale threshold; initial recommendation: 3 seconds.
- [x] Set the completed-candle grace period.
- [ ] Obtain and configure Public API credentials. **Operator action:** templates are ready; real values must remain outside source control.
- [x] Choose local, staging, and production deployment environments.
- [x] Configure PostgreSQL connection settings.
- [x] Decide whether Alpaca comparison mode will be implemented.
- [x] Document the expected Webull API approval path and timing.

## 0.2 Repository and Development Standards

- [x] Create the backend project structure.
- [x] Create the frontend project structure.
- [x] Add environment-variable templates without secrets.
- [x] Add Python formatting, linting, and type-checking configuration.
- [x] Add React/TypeScript formatting, linting, and type-checking configuration.
- [x] Add backend and frontend test frameworks.
- [x] Add database migration tooling.
- [x] Add structured logging conventions.
- [x] Add UTC storage and Eastern Time display conventions.
- [x] Define shared enums for order states, signal states, exit reasons, and execution modes.
- [x] Define a versioned API contract between backend and frontend.

## 0.3 Initial Architecture Contracts

- [x] Define the `MarketDataProvider` interface.
- [x] Define the `ExecutionBroker` interface.
- [x] Define canonical models for bars, quotes, expirations, option contracts, and option chains.
- [x] Define canonical models for orders, replacements, fills, positions, account state, and cash events.
- [x] Ensure strategy components cannot import provider-specific execution code.
- [x] Define idempotency rules for order events, fills, and ledger transactions.
- [x] Define application startup recovery behavior.

### Phase 0 Completion Gate

- [x] All unresolved Version 1 settings have documented defaults.
- [x] Backend, frontend, database, tests, and migrations run locally.
- [x] Broker-neutral interfaces and canonical data models are approved.
- [x] No secrets exist in the repository.
- [x] GitHub Actions CI passes on `main`.
- [x] Repository line endings are standardized through `.gitattributes`.

---

# Phase 1 — Public Market Data, Internal Paper Broker, and PostgreSQL Ledger

## 1.1 PostgreSQL Ledger

Create and migrate the core tables:

- [ ] `paper_accounts`
- [ ] `account_snapshots`
- [ ] `orders`
- [ ] `order_events`
- [ ] `fills`
- [ ] `positions`
- [ ] `position_lots`
- [ ] `cash_transactions`
- [ ] `strategy_signals`
- [ ] `risk_decisions`
- [ ] `market_snapshots`
- [ ] `daily_performance`
- [ ] `system_events`

Ledger requirements:

- [ ] Store every order state transition.
- [ ] Store every partial fill as an individual fill event.
- [ ] Store every cash movement as an immutable event.
- [ ] Support the approved order states:
  - [ ] `CREATED`
  - [ ] `RESERVED`
  - [ ] `SUBMITTED`
  - [ ] `WORKING`
  - [ ] `PARTIALLY_FILLED`
  - [ ] `REPLACED`
  - [ ] `FILLED`
  - [ ] `CANCEL_REQUESTED`
  - [ ] `CANCELED`
  - [ ] `REJECTED`
  - [ ] `EXPIRED`
- [ ] Support the approved cash event types:
  - [ ] `INITIAL_DEPOSIT`
  - [ ] `BUY_PREMIUM`
  - [ ] `SELL_PROCEEDS`
  - [ ] `COMMISSION`
  - [ ] `REGULATORY_FEE`
  - [ ] `ADJUSTMENT`
  - [ ] `RESET`
- [ ] Reproduce cash, buying power, positions, and P&L from fills and cash events.
- [ ] Create a new ledger session when the paper account is reset.
- [ ] Preserve prior sessions and history after reset.

## 1.2 Public Market Data Provider

Underlying data:

- [x] Fetch underlying quotes for SPY, QQQ, NVDA, TSLA, GOOGL, and AAPL.
- [x] Fetch five-minute OHLCV bars.
- [x] Build completed five-minute candles only.
- [x] Track quote and candle timestamps.
- [ ] Build completed fifteen-minute candles from three contiguous completed five-minute regular-session candles for technical exits.
- [ ] Detect stale underlying data.

Option data:

- [ ] Fetch actual expiration lists from Public.
- [ ] Fetch option chains by returned expiration.
- [ ] Fetch option bid, ask, bid size, and ask size.
- [ ] Fetch option volume and open interest.
- [ ] Fetch option Greeks when available.
- [ ] Repeatedly update quotes for working orders and open positions.
- [ ] Use Public's exact returned option symbols.
- [ ] Detect stale option quotes.
- [ ] Add reconnect and backoff behavior.
- [ ] Record connection-loss and reconnection events.

Expiration rules:

- [ ] For NVDA, TSLA, GOOGL, and AAPL, choose the nearest available listed expiration.
- [ ] Allow Monday, Wednesday, and Friday weekly expirations when Public lists them.
- [ ] Permit 0DTE.
- [ ] Never generate expiration dates independently.
- [ ] Evaluate the next listed expiration when the nearest expiration has no qualifying contract.
- [ ] For SPY and QQQ, use the nearest available expiration without restricting weekdays.
- [ ] Calculate and expose exact DTE.

## 1.3 Indicator Engine

- [ ] Calculate session VWAP from completed five-minute session data.
- [ ] Calculate the five-minute 9-period EMA for entries.
- [ ] Calculate five-minute MACD 12/26/9.
- [ ] Calculate the five-minute MACD histogram.
- [ ] Compare the current five-minute histogram with the prior histogram.
- [ ] Calculate the fifteen-minute 9-period EMA for technical exits.
- [ ] Recalculate entry indicators only when a five-minute candle completes.
- [ ] Recalculate the technical-exit EMA only when a fifteen-minute candle completes.
- [ ] Prevent incomplete five-minute candles from creating signals.
- [ ] Prevent incomplete, stale, missing, or non-contiguous five-minute source candles from producing a fifteen-minute technical-exit candle.
- [ ] Persist indicator snapshots with their timeframe for each decision.
- [ ] Unit-test five-minute entry indicators and the fifteen-minute exit EMA against known reference values.

## 1.4 Strategy Engine — EMA Bounce

- [ ] Evaluate all EMA-bounce setup, confirmation, and entry conditions from completed five-minute candles only.

Call setup:

- [ ] Require price above session VWAP.
- [ ] Detect interaction with the 9 EMA.
- [ ] Require the bounce candle to close above the 9 EMA.
- [ ] Require a bullish bounce candle.
- [ ] Require MACD line above signal line.
- [ ] Require a positive MACD histogram.
- [ ] Require the histogram to strengthen.
- [ ] Require the next five-minute candle to open above the 9 EMA.
- [ ] Evaluate entry only after the confirming candle opens.

Put setup:

- [ ] Require price below session VWAP.
- [ ] Detect interaction with the 9 EMA.
- [ ] Require the bounce candle to close below the 9 EMA.
- [ ] Require a bearish bounce candle.
- [ ] Require MACD line below signal line.
- [ ] Require a negative MACD histogram.
- [ ] Require the histogram to strengthen in the bearish direction.
- [ ] Require the next five-minute candle to open below the 9 EMA.
- [ ] Evaluate entry only after the confirming candle opens.

Invalidation and lifecycle:

- [ ] Invalidate the setup when the next candle opens on the wrong side of the EMA.
- [ ] Cancel a pending entry when the underlying setup becomes invalid.
- [ ] Require a new EMA-bounce setup after cancellation or expiration.
- [ ] Do not automatically retry an old setup.
- [ ] Record accepted and rejected setup reasons.

## 1.5 Trading Schedule Service

All schedule logic uses Eastern Time:

- [ ] Block entries from 9:30 AM through 9:59:59 AM.
- [ ] Enable entries from 10:00 AM through 11:29:59 AM.
- [ ] Block new entries from 11:30 AM through 1:59:59 PM.
- [ ] Continue managing existing positions during the midday block.
- [ ] Enable entries from 2:00 PM through 3:29:59 PM.
- [ ] At 3:30 PM, cancel all working orders.
- [ ] At 3:30 PM, force close all bot-managed positions.
- [ ] Disable the strategy from 3:30 PM through market close.
- [ ] Ensure the force-flat rule overrides timers and profit targets.
- [ ] Handle weekends, holidays, half-days, and daylight-saving changes safely.

## 1.6 Contract Selector

Filtering:

- [ ] Search calls only for bullish underlying signals.
- [ ] Search puts only for bearish underlying signals.
- [ ] Require absolute delta from 0.45 through 0.60.
- [ ] Prefer ATM or one strike ITM.
- [ ] Enforce the smaller of a $0.15 spread or 10% of midpoint.
- [ ] Require a minimum bid of $0.20.
- [ ] Require minimum option volume of 100.
- [ ] Require minimum open interest of 500.
- [ ] Reject zero-bid contracts.
- [ ] Prefer the most liquid qualifying contract.

Ranking:

- [ ] Rank correct nearest expiration first.
- [ ] Rank target delta second.
- [ ] Rank ATM or one strike ITM third.
- [ ] Rank approved spread fourth.
- [ ] Rank volume fifth.
- [ ] Rank open interest sixth.
- [ ] Rank displayed size seventh.
- [ ] Rank lowest spread percentage eighth.
- [ ] Persist every selected and rejected contract with reasons.

## 1.7 Risk Engine and Buying-Power Allocation

Symbol selection:

- [ ] Allow SPY, QQQ, NVDA, TSLA, GOOGL, and AAPL to be independently enabled.
- [ ] Disable signal evaluation and entries when no symbols are selected.
- [ ] Monitor and allocate capacity only to selected symbols.
- [ ] Apply symbol-selection changes only to future entries.
- [ ] Do not resize existing positions when selection changes.

Capacity calculations:

- [ ] Calculate total strategy capacity as available buying power × 50%.
- [ ] Divide total strategy capacity by the number of selected symbols.
- [ ] Treat per-symbol capacity as a maximum, not a target.
- [ ] Leave unused capacity uncommitted.
- [ ] Calculate remaining strategy capacity after positions and reservations.
- [ ] Reserve capital when an entry order is submitted.
- [ ] Calculate reservation using maximum permitted entry price × contracts × 100.
- [ ] Release unused reservations after fills, cancellation, rejection, or expiration.
- [ ] Recalculate risk and buying power before every order replacement.

Position sizing:

- [ ] Limit each position to five contracts.
- [ ] Size using the maximum permitted entry price.
- [ ] Keep normal sizing within the symbol allocation.
- [ ] Allow a one-contract exception only when normal sizing returns zero.
- [ ] Prevent the one-contract exception from breaching the portfolio-wide 50% ceiling.
- [ ] Require sufficient paper buying power.
- [ ] Prohibit averaging down.
- [ ] Prohibit adding after entry.

Occupancy and correlation limits:

- [ ] Allow only one active directional position per underlying.
- [ ] Prevent calls and puts on the same underlying from coexisting.
- [ ] Treat a pending entry as occupying the symbol.
- [ ] Keep the symbol occupied until the position is flat and related orders are resolved.
- [ ] Limit the portfolio to two simultaneous positions.
- [ ] Prevent SPY and QQQ from being open at the same time.

Daily circuit breakers:

- [ ] Stop new entries at a 3% realized loss from starting account value.
- [ ] Limit the bot to six entries per day.
- [ ] Limit each symbol to two entries per day.
- [ ] Stop trading after three consecutive losing trades.
- [ ] Apply a 15-minute symbol cooldown after a stopped trade.
- [ ] Block same-direction re-entry on the immediately following five-minute candle.
- [ ] Implement a manually resettable emergency kill switch.

## 1.8 Internal Paper Broker

Account model:

- [ ] Implement cash-style long-options buying power.
- [ ] Do not simulate margin.
- [ ] Deduct premium when buys fill.
- [ ] Return sell proceeds to cash when positions close.
- [ ] Apply configurable fees and slippage.
- [ ] Calculate net account value from cash and current liquidation value.
- [ ] Expose cash, buying power, reservations, committed capital, and net account value.

Order workflow:

- [ ] Submit entries at midpoint at T+0 seconds.
- [ ] Replace unfilled quantity at midpoint plus one valid tick at T+3 seconds.
- [ ] Replace up to the original ask at T+6 seconds.
- [ ] Cancel all remaining unfilled quantity at T+10 seconds.
- [ ] Never exceed the original ask by more than one valid tick.
- [ ] Cancel when the setup becomes invalid.
- [ ] Cancel when the spread exceeds the approved maximum.
- [ ] Keep partial fills as the final position size.
- [ ] Do not chase the unfilled remainder after ten seconds.

Conservative fill model:

- [ ] Treat a buy as marketable only when limit price is at or above the current ask.
- [ ] Keep an inside-spread buy working until a later ask reaches the limit.
- [ ] Treat a sell as marketable only when limit price is at or below the current bid.
- [ ] Cap buy fills by displayed ask size when available.
- [ ] Cap sell fills by displayed bid size when available.
- [ ] Do not assume unlimited liquidity when quote size is unavailable.
- [ ] Record partial fills as separate events.
- [ ] Prevent any fill from stale option data.

## 1.9 Position Manager and Exit Engine

Hard stop:

- [ ] Calculate the hard-stop threshold as average fill × 0.80.
- [ ] Trigger the hard stop from executable option bid.
- [ ] Fill from the next valid bid with configured slippage.
- [ ] Allow realized loss to exceed 20% during fast markets.

Technical stop:

- [ ] Exit calls when a completed fifteen-minute underlying candle closes below the fifteen-minute 9 EMA.
- [ ] Exit puts when a completed fifteen-minute underlying candle closes above the fifteen-minute 9 EMA.
- [ ] Build each fifteen-minute candle from exactly three contiguous completed regular-session five-minute candles.
- [ ] Prevent missing, stale, incomplete, or non-contiguous source candles from triggering the technical stop.
- [ ] Keep the option-price hard stop, profit targets, break-even stop, 30-minute time stop, emergency exit, and 3:30 PM force-flat rule continuously active without waiting for a fifteen-minute candle.

Time and end-of-day stops:

- [ ] Start the 30-minute timer from the first fill.
- [ ] Do not reset the timer after partial exits.
- [ ] Exit remaining quantity at the 30-minute limit.
- [ ] Override the timer with the 3:30 PM force-flat rule.

Scale-out ladder:

- [ ] Set Target 1 at average entry × 1.30.
- [ ] Set Target 2 at average entry × 1.50.
- [ ] Set Target 3 at average entry × 1.75.
- [ ] Use the approved quantity ladder for one through five contracts.
- [ ] Use executable option prices for target decisions.
- [ ] After Target 1, move the remaining stop to break-even plus estimated round-trip fees.
- [ ] Never move a stop in a direction that increases risk.
- [ ] Keep the runner until a completed fifteen-minute EMA violation, time stop, hard stop, or force-flat.
- [ ] Persist every target fill and stop adjustment.

## 1.10 P&L and Performance Service

- [ ] Calculate option mark as `(bid + ask) ÷ 2`.
- [ ] Calculate mark P&L.
- [ ] Calculate liquidation P&L using current bid.
- [ ] Use liquidation P&L for risk decisions.
- [ ] Calculate realized P&L from allocated entry cost, proceeds, and fees.
- [ ] Calculate daily P&L from realized P&L, unrealized P&L, and fees.
- [ ] Distinguish account-wide values from bot-only values.
- [ ] Reconcile position-level P&L with ledger-level P&L.
- [ ] Persist account snapshots and daily performance.

## 1.11 Backend API and WebSocket Foundation

- [ ] Create FastAPI health and readiness endpoints.
- [ ] Create account summary endpoints.
- [ ] Create symbol-selection endpoints.
- [ ] Create strategy-control endpoints.
- [ ] Create positions endpoints.
- [ ] Create orders and order-events endpoints.
- [ ] Create history and export endpoints.
- [ ] Create performance endpoints.
- [ ] Create logs and audit endpoints.
- [ ] Create settings endpoints.
- [ ] Create a WebSocket endpoint for live updates.
- [ ] Define WebSocket message schemas and sequence numbers.
- [ ] Support reconnect and state resynchronization.
- [ ] Add authentication or local-access restrictions appropriate to deployment.

### Phase 1 Completion Gate

- [ ] A full paper trade can run from signal through contract selection, reservation, order lifecycle, fills, exits, ledger settlement, and P&L without the frontend.
- [ ] Every account value is reproducible from immutable ledger events.
- [ ] Unit and integration tests cover schedule, strategy, contract selection, risk, order workflow, partial fills, exits, and P&L.
- [ ] Stale data cannot create orders, fills, stops, or P&L updates.
- [ ] The strategy engine remains independent of Public-specific and broker-specific execution logic.

---

# Phase 2 — React Frontend, History, Downloads, and Performance

## 2.1 Frontend Foundation

- [ ] Create the React and TypeScript application.
- [ ] Add routing for all primary pages.
- [ ] Add a typed API client.
- [ ] Add a typed WebSocket client.
- [ ] Add reconnect and full-state resynchronization.
- [ ] Add global error and loading states.
- [ ] Add responsive desktop layouts.
- [ ] Display Eastern Time consistently.
- [ ] Avoid copying proprietary Webull assets.

## 2.2 Persistent Account Summary

Display on all primary pages:

- [ ] Net account value.
- [ ] Available buying power.
- [ ] 50% bot allocation ceiling.
- [ ] Capital committed.
- [ ] Capital reserved.
- [ ] Remaining bot capacity.
- [ ] Open P&L.
- [ ] Daily P&L.
- [ ] Realized P&L.
- [ ] Bot status.
- [ ] Public market-data connection status.
- [ ] Current execution mode.
- [ ] Source labels for market data, execution, mode, and future broker.
- [ ] Persistent emergency-stop control.

## 2.3 Main Navigation

- [ ] Dashboard
- [ ] Positions
- [ ] Orders
- [ ] Performance
- [ ] Trade History
- [ ] Strategy
- [ ] Logs
- [ ] Settings

## 2.4 Dashboard

Controls:

- [ ] Start bot.
- [ ] Pause new entries.
- [ ] Resume entries.
- [ ] Cancel all orders.
- [ ] Flatten all positions.
- [ ] Trigger emergency stop.
- [ ] Select and deselect symbols.
- [ ] Show dynamic per-symbol capacity.

Each selected symbol card:

- [ ] Underlying price.
- [ ] Above or below VWAP.
- [ ] Relationship to 9 EMA.
- [ ] MACD status.
- [ ] Selected expiration.
- [ ] Selected contract.
- [ ] Maximum affordable contracts.
- [ ] Signal state.
- [ ] Position state.
- [ ] Cooldown state.
- [ ] Trades today.
- [ ] Quote freshness timestamp.

## 2.5 Positions Page

Position table:

- [ ] Underlying.
- [ ] Full option contract.
- [ ] Call or put.
- [ ] Expiration.
- [ ] DTE.
- [ ] Strike.
- [ ] Current quantity.
- [ ] Initial quantity.
- [ ] Average entry.
- [ ] Current bid and ask.
- [ ] Mark.
- [ ] Total cost.
- [ ] Market value.
- [ ] Mark P&L.
- [ ] Liquidation P&L.
- [ ] Open P&L percentage.
- [ ] Daily P&L.
- [ ] Holding time.
- [ ] Current stop.
- [ ] Next target.
- [ ] Strategy state.
- [ ] Manual close action.

Position detail panel:

- [ ] Entry rationale.
- [ ] Five-minute underlying chart.
- [ ] VWAP overlay.
- [ ] 9 EMA overlay.
- [ ] MACD panel.
- [ ] Entry and exit markers.
- [ ] Scale-out history.
- [ ] Stop movement history.
- [ ] Current option spread.
- [ ] Public quote timestamps.
- [ ] Internal order IDs.
- [ ] Holding timer.
- [ ] Manual close control.

## 2.6 Orders Page

Subtabs:

- [ ] Working Orders
- [ ] Filled Orders
- [ ] Canceled Orders
- [ ] Rejected Orders
- [ ] All Today

Order table:

- [ ] Submitted time.
- [ ] Underlying.
- [ ] Contract.
- [ ] Side.
- [ ] Filled quantity versus total quantity.
- [ ] Limit price.
- [ ] Stop price.
- [ ] Order type.
- [ ] Time in force.
- [ ] Status.
- [ ] Average fill.
- [ ] Filled time.
- [ ] Internal order ID.
- [ ] Future broker order ID field.
- [ ] Strategy reason.
- [ ] Cancel and inspect actions.

Order detail:

- [ ] Initial midpoint submission.
- [ ] Each replacement.
- [ ] Every partial fill.
- [ ] Cancellation event.
- [ ] Rejection reason.
- [ ] Final state.

## 2.7 Trade History and Downloads

Filters:

- [ ] Today.
- [ ] This week.
- [ ] This month.
- [ ] Custom date range.
- [ ] Symbol.
- [ ] Calls or puts.
- [ ] Winning or losing trades.
- [ ] Paper or future live mode.
- [ ] Exit reason.
- [ ] Order status.

Completed-trade fields:

- [ ] Trade ID.
- [ ] Symbol.
- [ ] Contract.
- [ ] Direction.
- [ ] Entry and exit time.
- [ ] Holding time.
- [ ] Initial quantity.
- [ ] Average entry and exit.
- [ ] Gross P&L.
- [ ] Fees.
- [ ] Net P&L.
- [ ] Return percentage.
- [ ] Maximum favorable excursion.
- [ ] Maximum adverse excursion.
- [ ] Entry reason.
- [ ] Exit reason.
- [ ] DTE at entry.
- [ ] Result.

Exports:

- [ ] CSV export.
- [ ] JSON export.
- [ ] Orders export.
- [ ] Fills export.
- [ ] Completed trades export.
- [ ] Positions export.
- [ ] Daily performance export.
- [ ] Signal history export.
- [ ] Full audit history export.
- [ ] Include fill-level detail rather than only summarized trades.

## 2.8 Performance Page

Views:

- [ ] Account P&L.
- [ ] Bot P&L.
- [ ] Symbol P&L.
- [ ] Strategy P&L.

Date ranges:

- [ ] Today.
- [ ] 5D.
- [ ] 1M.
- [ ] 3M.
- [ ] 6M.
- [ ] YTD.
- [ ] 1Y.
- [ ] All.
- [ ] Custom.

Metrics:

- [ ] Net P&L.
- [ ] Gross P&L.
- [ ] Realized P&L.
- [ ] Unrealized P&L.
- [ ] Fees.
- [ ] Win rate.
- [ ] Profit factor.
- [ ] Average winner.
- [ ] Average loser.
- [ ] Average holding time.
- [ ] Maximum drawdown.
- [ ] Largest win.
- [ ] Largest loss.
- [ ] Trade count.
- [ ] Consecutive wins.
- [ ] Consecutive losses.

Charts and summaries:

- [ ] Cumulative net P&L.
- [ ] Daily realized P&L.
- [ ] Drawdown.
- [ ] Gross versus net performance.
- [ ] P&L by symbol.
- [ ] Performance calendar.
- [ ] Prepare separation of bot and manual trades for future live integrations.

## 2.9 Strategy, Logs, and Settings Pages

Strategy page:

- [ ] Configure enabled symbols.
- [ ] Configure expiration mode, 0DTE permission, and maximum DTE.
- [ ] Display the five-contract limit.
- [ ] Configure daily trade limits and cooldowns.
- [ ] Configure or display VWAP, EMA 9, and MACD 12/26/9.
- [ ] Configure the strengthening-histogram requirement.
- [ ] Configure or lock completed-candle and confirming-open rules.
- [ ] Configure or display risk settings.
- [ ] Configure or display scale-out settings.
- [ ] Prevent unsafe settings from bypassing hard safety limits.

Logs page:

- [ ] Search logs.
- [ ] Filter logs by symbol, event type, severity, order, and trade.
- [ ] Inspect complete event payloads.
- [ ] Download logs.
- [ ] Highlight stale data, disconnections, circuit breakers, and emergency events.

Settings page:

- [ ] Configure paper-account values permitted by the specification.
- [ ] Configure fees and slippage.
- [ ] Configure stale thresholds.
- [ ] Configure data and deployment settings safely.
- [ ] Display masked credential status without exposing secrets.
- [ ] Require confirmation before account reset.
- [ ] Create a new ledger session on reset.

### Phase 2 Completion Gate

- [ ] Every backend function needed for paper operation is controllable or observable from the frontend.
- [ ] Account, positions, orders, history, performance, strategy, logs, and settings remain synchronized through WebSocket updates.
- [ ] Emergency stop and manual close remain available during partial backend or data-provider failures.
- [ ] CSV and JSON exports reconcile with the ledger.
- [ ] The UI always displays `Market Data: Public`, `Execution: Internal Paper`, and `Mode: PAPER` for Version 1.

---

# Phase 3 — Live Paper Operation During Market Hours

## 3.1 Session Startup

- [ ] Start services before market open.
- [ ] Verify database connectivity.
- [ ] Verify Public connectivity.
- [ ] Load the active paper-account session.
- [ ] Rebuild account and position state from the ledger.
- [ ] Reconcile unresolved orders from the prior session.
- [ ] Load selected symbols and strategy settings.
- [ ] Warm sufficient historical bars for indicators.
- [ ] Verify all quote timestamps before enabling signals.
- [ ] Keep entries disabled until readiness checks pass.

## 3.2 Market-Hours Operation

- [ ] Run all six selectable symbols concurrently when enabled.
- [ ] Form five-minute candles reliably.
- [ ] Evaluate signals only on completed candles and confirming opens.
- [ ] Refresh option expirations and chains when needed.
- [ ] Maintain fresh option quotes for orders and positions.
- [ ] Process entry replacements at T+3, T+6, and cancellation at T+10.
- [ ] Process partial fills conservatively.
- [ ] Manage hard stops, technical stops, targets, runners, and timers.
- [ ] Publish live updates to the frontend.
- [ ] Persist every material event before or atomically with state changes.

## 3.3 Operational Controls

- [ ] Pause new entries without interrupting position management.
- [ ] Resume entries only when data and risk checks pass.
- [ ] Cancel all working orders safely.
- [ ] Flatten all positions safely.
- [ ] Trigger and manually reset the emergency kill switch.
- [ ] Prevent new entries after any active circuit breaker.
- [ ] Recover safely from a Public disconnect.
- [ ] Recover safely from a frontend disconnect.
- [ ] Recover safely from a backend restart.
- [ ] Prevent duplicate orders after reconnect or restart.

## 3.4 End-of-Day Lifecycle

- [ ] At 3:30 PM ET, cancel every working order.
- [ ] At 3:30 PM ET, flatten every bot-managed position.
- [ ] Verify the account is flat.
- [ ] Prevent entries through market close.
- [ ] Produce the daily account snapshot.
- [ ] Produce the daily performance record.
- [ ] Reconcile cash, fills, positions, fees, and P&L.
- [ ] Flag any unresolved order or ledger discrepancy.
- [ ] Preserve downloadable logs and audit history.

## 3.5 Observation Runbook

- [ ] Create a market-open readiness checklist.
- [ ] Create a stale-data incident procedure.
- [ ] Create a provider-disconnection procedure.
- [ ] Create an order-state discrepancy procedure.
- [ ] Create a failed force-flat procedure.
- [ ] Create a database recovery procedure.
- [ ] Create a daily reconciliation procedure.
- [ ] Create an emergency-stop procedure.

### Phase 3 Completion Gate

- [ ] Complete multiple full market sessions without manual database repair.
- [ ] No duplicate order or fill events occur during reconnects or restarts.
- [ ] All positions are reliably flat by the end-of-day gate.
- [ ] Every session produces complete logs, trade history, exports, and performance data.
- [ ] Operational failures fail closed: no new entries occur when safety or data state is uncertain.

---

# Phase 4 — Validate Fill Quality, Slippage, Stops, Scale-Outs, and P&L

## 4.1 Fill-Model Validation

- [ ] Compare simulated buy fills with historical or observed ask prices.
- [ ] Compare simulated sell fills with historical or observed bid prices.
- [ ] Confirm inside-spread limits do not fill automatically.
- [ ] Confirm displayed-size limits constrain partial fills.
- [ ] Confirm unavailable quote size does not create unlimited fills.
- [ ] Confirm T+3 and T+6 replacements use valid ticks.
- [ ] Confirm no replacement exceeds the approved chase limit.
- [ ] Confirm unfilled quantity is canceled at T+10.
- [ ] Measure fill rate by symbol, spread, time of day, and order step.

## 4.2 Stop Validation

- [ ] Confirm hard stops trigger from executable bid.
- [ ] Confirm stop fills use the next valid bid plus configured slippage.
- [ ] Confirm losses can exceed the threshold during gaps or fast moves.
- [ ] Confirm technical stops use completed underlying candles.
- [ ] Confirm the 30-minute timer starts at first fill.
- [ ] Confirm partial exits do not reset the timer.
- [ ] Confirm 3:30 PM force-flat overrides all other exits.
- [ ] Confirm stale quotes cannot trigger or fill stops.

## 4.3 Scale-Out Validation

- [ ] Validate target prices from average entry.
- [ ] Validate the quantity ladder for one contract.
- [ ] Validate the quantity ladder for two contracts.
- [ ] Validate the quantity ladder for three contracts.
- [ ] Validate the quantity ladder for four contracts.
- [ ] Validate the quantity ladder for five contracts.
- [ ] Confirm Target 1 moves the remaining stop to break-even plus estimated fees.
- [ ] Confirm stops never loosen after being tightened.
- [ ] Confirm runners exit only through approved remaining exit rules.
- [ ] Confirm partial target fills are reflected correctly.

## 4.4 Buying Power and Risk Validation

- [ ] Test each selected-symbol allocation from one through six symbols.
- [ ] Confirm the portfolio never exceeds 50% of available buying power.
- [ ] Confirm pending entries reserve capital.
- [ ] Confirm replacement risk is recalculated.
- [ ] Confirm cancellation releases reservations.
- [ ] Confirm partial fills release excess reservation.
- [ ] Confirm one-contract exceptions never breach the total ceiling.
- [ ] Confirm only two simultaneous positions are possible.
- [ ] Confirm SPY and QQQ mutual exclusion.
- [ ] Confirm one active direction per underlying.
- [ ] Confirm all daily circuit breakers.

## 4.5 P&L Reconciliation

- [ ] Recalculate every trade from raw fills and fees.
- [ ] Recalculate every cash balance from cash events.
- [ ] Recalculate every position from fill lots.
- [ ] Compare mark P&L with midpoint calculations.
- [ ] Compare liquidation P&L with bid calculations.
- [ ] Confirm risk decisions use liquidation values.
- [ ] Confirm daily P&L includes realized, unrealized, and fees.
- [ ] Confirm account-wide and bot-only values remain distinct.
- [ ] Confirm frontend, exports, API, and ledger values match.
- [ ] Test account reset without overwriting history.

## 4.6 Strategy and Operational Review

- [ ] Measure setup frequency by symbol and time window.
- [ ] Measure contract rejection reasons.
- [ ] Measure entries blocked by risk rules.
- [ ] Measure stale-data incidents.
- [ ] Measure order cancellation and partial-fill rates.
- [ ] Measure stop slippage.
- [ ] Measure maximum favorable and adverse excursion.
- [ ] Review losses caused by spread, liquidity, and quote latency.
- [ ] Verify all deviations are observable in logs.
- [ ] Document whether any configurable default should change before broader testing.

### Phase 4 Completion Gate

- [ ] Ledger reconciliation has zero unexplained discrepancies.
- [ ] Fill behavior is conservative and repeatable.
- [ ] Stops, scale-outs, timers, and force-flat behavior pass deterministic scenario tests.
- [ ] Risk limits cannot be bypassed through concurrency, partial fills, replacements, or restarts.
- [ ] Performance metrics and exports match independently recalculated results.
- [ ] Version 1 paper behavior is approved for extended operation.

---

# Phase 5 — Optional Alpaca Paper Comparison Adapter

> **Optional:** This phase does not block the internal-paper Version 1 release.

## 5.1 Adapter Implementation

- [ ] Implement `AlpacaPaperBroker` behind the `ExecutionBroker` interface.
- [ ] Map canonical order models to Alpaca paper orders.
- [ ] Map Alpaca order states to internal order states.
- [ ] Map fills and partial fills into canonical fill events.
- [ ] Preserve Alpaca broker order IDs.
- [ ] Keep the internal ledger as the application audit record.
- [ ] Keep strategy logic unchanged.

## 5.2 Comparison Mode

- [ ] Run identical signals through internal-paper and Alpaca-paper paths without double-counting performance.
- [ ] Compare submission time, fill time, fill price, partial fills, and cancellations.
- [ ] Compare position and account reconciliation.
- [ ] Label every result by execution source.
- [ ] Prevent comparison mode from violating paper-mode safety constraints.

### Phase 5 Completion Gate

- [ ] Adapter-specific tests pass.
- [ ] Strategy code contains no Alpaca-specific branches.
- [ ] Comparison reports clearly separate internal and Alpaca results.
- [ ] Disabling Alpaca leaves internal paper operation unchanged.

---

# Phase 6 — Webull Broker Adapter After API Approval

## 6.1 Access and Capability Review

- [ ] Confirm approved Webull API access.
- [ ] Confirm supported account types.
- [ ] Confirm options permissions and order capabilities.
- [ ] Confirm authentication and token-refresh requirements.
- [ ] Confirm rate limits and streaming capabilities.
- [ ] Confirm order replacement and cancellation behavior.
- [ ] Confirm partial-fill reporting.
- [ ] Confirm position, balance, and buying-power fields.
- [ ] Confirm supported option symbology.
- [ ] Document any API limitations versus the internal broker interface.

## 6.2 Adapter Implementation

- [ ] Implement `WebullBroker` behind the `ExecutionBroker` interface.
- [ ] Map canonical orders to Webull orders.
- [ ] Map Webull states to internal order states.
- [ ] Store future broker order IDs.
- [ ] Normalize fills, fees, and partial fills.
- [ ] Reconcile Webull positions with internal records.
- [ ] Reconcile Webull buying power with bot capacity calculations.
- [ ] Handle token expiry, reconnects, rate limits, and rejected requests.
- [ ] Keep Public as the approved market-data source unless separately changed.
- [ ] Keep strategy logic free of Webull-specific branches.

## 6.3 Security and Controls

- [ ] Store credentials using an approved secret-management method.
- [ ] Prevent live credentials from being used in development tests.
- [ ] Add explicit execution-mode labels.
- [ ] Add environment-level live-order locks.
- [ ] Add account and permission verification at startup.
- [ ] Add duplicate-order protection.
- [ ] Add broker-response idempotency.
- [ ] Add fail-closed behavior for ambiguous order state.

### Phase 6 Completion Gate

- [ ] Webull adapter passes contract tests against the `ExecutionBroker` interface.
- [ ] The application can switch brokers without strategy-engine changes.
- [ ] Broker and ledger reconciliation is deterministic.
- [ ] Live order submission remains disabled.

---

# Phase 7 — Webull Shadow Mode and Order-Preview Comparison

## 7.1 Shadow Mode

- [ ] Generate the order that would be sent to Webull without transmitting it.
- [ ] Record previewed contract, side, quantity, order type, limit, and timestamps.
- [ ] Compare previewed orders with internal-paper orders.
- [ ] Compare Webull account constraints with internal risk decisions.
- [ ] Surface preview rejections and capability differences.
- [ ] Display `SHADOW` prominently in the frontend.
- [ ] Prevent all broker order-transmission endpoints in shadow mode.

## 7.2 Comparison and Reconciliation

- [ ] Compare option-symbol mapping.
- [ ] Compare calculated quantity.
- [ ] Compare buying-power impact.
- [ ] Compare order-price rounding and tick size.
- [ ] Compare cancel and replace semantics.
- [ ] Compare estimated fees.
- [ ] Record every mismatch with severity and resolution status.
- [ ] Require zero unexplained critical mismatches before approval mode.

### Phase 7 Completion Gate

- [ ] Shadow mode cannot transmit an order under any code path.
- [ ] Previewed orders match approved strategy and risk decisions.
- [ ] All critical mapping, sizing, and order-state discrepancies are resolved.
- [ ] Audit logs clearly distinguish paper orders from Webull previews.

---

# Phase 8 — Webull Live Approval Mode

> In approval mode, the bot may prepare an order, but a human must explicitly approve transmission.

## 8.1 Human Approval Workflow

- [ ] Present contract, expiration, DTE, direction, quantity, limit, spread, and estimated cost.
- [ ] Present signal rationale and indicator state.
- [ ] Present account buying power and remaining bot capacity.
- [ ] Present active risk limits and current daily circuit-breaker state.
- [ ] Require explicit approval for every entry.
- [ ] Require explicit approval for material order replacement when configured.
- [ ] Record approver, timestamp, displayed values, and final submitted payload.
- [ ] Expire approvals when market data or risk state becomes stale.
- [ ] Revalidate setup, quote freshness, spread, and risk immediately before transmission.

## 8.2 Live Safety Controls

- [ ] Display `LIVE — APPROVAL REQUIRED` on every primary page.
- [ ] Preserve pause, cancel-all, flatten-all, manual close, and emergency stop.
- [ ] Preserve the 50% strategy ceiling.
- [ ] Preserve all position and daily risk limits.
- [ ] Preserve the 3:30 PM force-flat rule.
- [ ] Prevent submission when broker state is uncertain.
- [ ] Confirm broker order acknowledgment before marking submitted.
- [ ] Reconcile all fills and positions continuously.
- [ ] Alert on any broker-ledger discrepancy.
- [ ] Provide an immediate fallback to paper or disabled mode.

### Phase 8 Completion Gate

- [ ] Every live entry requires explicit human approval.
- [ ] Stale approvals cannot submit orders.
- [ ] Broker, ledger, frontend, and exported records reconcile.
- [ ] Emergency controls have been tested in a controlled live environment.
- [ ] Approval-mode operation is documented and formally accepted.

---

# Phase 9 — Optional Fully Automated Webull Execution

> **Optional and highest-risk phase:** Do not enable until all prior live gates are complete and sustained approval-mode evidence supports automation.

## 9.1 Automation Readiness

- [ ] Define minimum approval-mode sample size.
- [ ] Define acceptable broker-ledger discrepancy rate.
- [ ] Define acceptable rejection and duplicate-order rates.
- [ ] Define maximum observed stop slippage.
- [ ] Define operational uptime and recovery standards.
- [ ] Define rollback criteria.
- [ ] Complete legal, account, broker, and operational review.
- [ ] Approve the exact settings allowed in automated live mode.

## 9.2 Automated Execution Controls

- [ ] Enable automated entry transmission only in the approved environment.
- [ ] Keep live mode disabled by default at startup.
- [ ] Require an explicit daily enable action.
- [ ] Verify account, permissions, market-data, broker, ledger, and risk state before enabling.
- [ ] Maintain all approved entry, sizing, stop, scale-out, schedule, and circuit-breaker rules.
- [ ] Maintain manual close, flatten-all, and emergency stop.
- [ ] Fail closed on stale data, connection loss, ambiguous broker state, or reconciliation failure.
- [ ] Disable new entries automatically after any critical error.
- [ ] Record every automated decision and broker response.
- [ ] Support immediate rollback to approval, shadow, or paper mode.

## 9.3 Production Monitoring

- [ ] Monitor provider and broker connectivity.
- [ ] Monitor quote freshness.
- [ ] Monitor order acknowledgment latency.
- [ ] Monitor fill and replacement latency.
- [ ] Monitor broker-ledger reconciliation.
- [ ] Monitor risk utilization and circuit breakers.
- [ ] Monitor force-flat completion.
- [ ] Alert on duplicate, rejected, missing, or ambiguous orders.
- [ ] Alert on open positions after the force-flat deadline.
- [ ] Produce daily automated reconciliation and incident reports.

### Phase 9 Completion Gate

- [ ] Fully automated live execution has formal approval.
- [ ] All live safeguards remain active and cannot be bypassed through normal settings.
- [ ] Production monitoring and alerting cover all critical failure modes.
- [ ] Rollback is tested and documented.
- [ ] Each live session is independently reconcilable from broker and ledger records.

---

# Cross-Phase Testing Checklist

## Unit Tests

- [ ] Indicator calculations.
- [ ] Candle completion and session boundaries.
- [ ] EMA-bounce detection and invalidation.
- [ ] Expiration selection and DTE calculation.
- [ ] Contract filters and ranking.
- [ ] Buying-power and reservation calculations.
- [ ] Position sizing and one-contract exception.
- [ ] Position occupancy and mutual exclusion.
- [ ] Entry replacement timeline.
- [ ] Partial-fill behavior.
- [ ] Hard, technical, time, and force-flat exits.
- [ ] Scale-out quantities and stop movement.
- [ ] Daily circuit breakers and cooldowns.
- [ ] P&L and fee calculations.
- [ ] Ledger reconstruction.

## Integration Tests

- [ ] Public provider to canonical market-data models.
- [ ] Strategy to contract selector.
- [ ] Contract selector to risk engine.
- [ ] Risk engine to broker reservation.
- [ ] Broker order events to ledger.
- [ ] Fills to positions and cash.
- [ ] Position exits to realized P&L.
- [ ] Backend API to frontend state.
- [ ] WebSocket reconnect and state recovery.
- [ ] CSV and JSON exports to ledger records.

## Scenario Tests

- [ ] No symbols selected.
- [ ] One through six symbols selected.
- [ ] Valid call setup.
- [ ] Valid put setup.
- [ ] Confirming candle opens on wrong side of EMA.
- [ ] No qualifying option contract.
- [ ] Spread widens after order submission.
- [ ] Setup invalidates during entry workflow.
- [ ] No fill.
- [ ] Partial fill at each order step.
- [ ] Hard stop through a gap.
- [ ] Technical stop and profit target occur close together.
- [ ] 30-minute stop during partial scale-out.
- [ ] 3:30 PM force-flat during working entry or exit orders.
- [ ] Public connection loss.
- [ ] Stale underlying quote.
- [ ] Stale option quote.
- [ ] Backend restart with open position.
- [ ] Database transaction failure.
- [ ] Emergency stop with pending orders and open positions.

## Concurrency and Failure Tests

- [ ] Two symbols signal simultaneously.
- [ ] SPY and QQQ signal simultaneously.
- [ ] Two entry requests target the same underlying.
- [ ] Account capacity changes during replacement.
- [ ] Duplicate provider message.
- [ ] Duplicate broker callback.
- [ ] Out-of-order order events.
- [ ] Network timeout after order submission but before acknowledgment.
- [ ] Restart during a partial fill.
- [ ] Restart during force-flat.

---

# Cross-Phase Security and Operations Checklist

- [ ] Store secrets outside source control.
- [ ] Mask credentials and tokens in logs.
- [ ] Apply least-privilege database permissions.
- [ ] Protect state-changing API endpoints.
- [ ] Validate and sanitize all API inputs.
- [ ] Add request and event correlation IDs.
- [ ] Add structured error reporting.
- [ ] Add database backups and restore tests.
- [ ] Add retention rules for market snapshots and logs.
- [ ] Add deployment rollback procedures.
- [ ] Add health, readiness, and liveness checks.
- [ ] Add clock-drift detection for schedule-critical services.
- [ ] Add observability for latency, stale data, fills, P&L, and risk utilization.
- [ ] Document incident severity and escalation criteria.

---

# Documentation Checklist

- [ ] Architecture overview.
- [ ] Local development setup.
- [ ] Environment-variable reference.
- [ ] Database migration and recovery guide.
- [ ] Public API integration guide.
- [ ] Internal paper fill-model specification.
- [ ] Strategy and risk-rule specification.
- [ ] API and WebSocket contract.
- [ ] Frontend user guide.
- [ ] Daily market-hours runbook.
- [ ] Emergency-stop and force-flat runbook.
- [ ] Ledger reconciliation guide.
- [ ] Export field dictionary.
- [ ] Alpaca comparison guide, when implemented.
- [ ] Webull shadow, approval, and live-mode guides, when implemented.
- [ ] Release notes and known limitations for every release.

---

# Version 1 Paper-Release Acceptance Checklist

- [ ] Phase 0 is complete.
- [ ] Phase 1 is complete.
- [ ] Phase 2 is complete.
- [ ] Phase 3 is complete.
- [ ] Phase 4 is complete.
- [ ] Public is the displayed and actual market-data source.
- [ ] Internal Paper is the displayed and actual execution source.
- [ ] `Mode: PAPER` is always visible.
- [ ] No live broker order path is enabled.
- [ ] Strategy capacity never exceeds 50% of available buying power.
- [ ] Maximum position size is five contracts.
- [ ] Maximum simultaneous positions is two.
- [ ] SPY and QQQ mutual exclusion is enforced.
- [ ] All approved daily circuit breakers are enforced.
- [ ] All positions and orders are resolved at 3:30 PM ET.
- [ ] Stale data fails closed.
- [ ] Emergency stop works from every primary page.
- [ ] Manual position closure works.
- [ ] Ledger, API, frontend, and exports reconcile.
- [ ] Every automated decision is auditable.
- [ ] Configuration, deployment, recovery, and operating procedures are documented.

---

# Phase Status Summary

| Phase | Scope | Required for Version 1 | Status |
|---:|---|:---:|---|
| 0 | Decisions, repository, interfaces, and foundation | Yes | Not started |
| 1 | Public data, paper broker, strategy, risk, ledger, backend | Yes | Not started |
| 2 | React frontend, history, downloads, and performance | Yes | Not started |
| 3 | Live paper operation during market hours | Yes | Not started |
| 4 | Validation and reconciliation | Yes | Not started |
| 5 | Alpaca paper comparison adapter | No | Optional |
| 6 | Webull broker adapter | No | Blocked by API approval |
| 7 | Webull shadow and preview mode | No | Future |
| 8 | Webull human-approval live mode | No | Future |
| 9 | Fully automated Webull execution | No | Optional future |

# 5-Minute Options Scalper Bot

A broker-neutral intraday options scalping application with a Python backend, React frontend, Public market data, and an internal paper-trading ledger.

The initial release is **paper trading only**. Public is used for market data, not for account balances, positions, paper orders, or execution. The architecture is designed so a future Webull execution adapter can replace the internal paper broker without changing the strategy engine.

---

## 1. Approved System Architecture

```text
React frontend
      |
      v
Python / FastAPI backend
├── StrategyEngine
├── IndicatorEngine
├── ContractSelector
├── RiskEngine
├── OrderManager
├── PositionManager
├── PerformanceService
├── MarketDataProvider
│   └── PublicMarketDataProvider
├── ExecutionBroker
│   ├── InternalPaperBroker      # Version 1
│   ├── AlpacaPaperBroker        # Optional future comparison adapter
│   └── WebullBroker             # Planned future execution adapter
└── Ledger
    └── PostgreSQL
```

### Provider responsibilities

#### Public

Public is used only for:

- Underlying OHLCV data.
- Five-minute bars.
- Underlying quotes.
- Option expiration lists.
- Option chains.
- Option bid/ask data.
- Option volume and open interest.
- Option Greeks when available.
- Repeated option quote updates for working orders and open positions.

Public is **not** used for:

- Paper account balances.
- Paper buying power.
- Paper orders.
- Paper fills.
- Paper positions.
- Paper P&L.
- Performance history.

#### Internal paper broker

The internal paper broker is the Version 1 execution venue and source of truth for:

- Buying power.
- Cash.
- Reserved capital.
- Orders.
- Fills.
- Partial fills.
- Positions.
- Realized P&L.
- Unrealized P&L.
- Fees.
- Performance history.
- Daily risk limits.

#### Future execution

- Webull is the preferred future live-execution destination if API access is approved.
- Alpaca paper trading may be added later as an optional comparison adapter.
- Strategy logic must remain broker-neutral.

---

## 2. Technology Stack

### Backend

- Python
- FastAPI
- WebSocket endpoint for live frontend updates
- PostgreSQL
- Async market-data and order-processing services

### Frontend

- React
- TypeScript
- WebSocket-driven live updates
- Webull-inspired account, positions, orders, history, and performance pages

---

## 3. Trading Universe

Selectable symbols:

```text
SPY
QQQ
NVDA
TSLA
GOOGL
AAPL
```

Only selected symbols:

- Receive active monitoring.
- Are evaluated for signals.
- Receive a buying-power allocation.
- Are eligible for paper orders.

If no symbols are selected, the strategy is disabled.

---

## 4. Trading Schedule

All times are Eastern Time.

| Time | Behavior |
|---|---|
| 9:30 AM–10:00 AM | No entries |
| 10:00 AM–11:30 AM | Prime entry window |
| 11:30 AM–2:00 PM | No new entries |
| 2:00 PM–3:30 PM | Afternoon entry window |
| 3:30 PM | Force flat and cancel all orders |
| 3:30 PM–4:00 PM | Strategy disabled |

Existing positions may continue to be managed after 11:30 AM until an exit rule or the 30-minute maximum holding time closes them.

The 3:30 PM force-flat rule overrides all other holding-time and profit-target rules.

---

## 5. Chart and Indicator Rules

The strategy uses separate entry and technical-exit timeframes:

- Entry setup, confirmation, VWAP, EMA, and MACD calculations use completed five-minute candles.
- The EMA technical exit uses completed fifteen-minute candles.
- Option-price hard stops, profit targets, break-even stops, time stops, emergency exits, and the 3:30 PM force-flat rule do not wait for a fifteen-minute candle.

### Entry indicators — five-minute

- Session VWAP
- 9-period EMA
- MACD 12/26/9

### Technical-exit indicator — fifteen-minute

- Calculate the 9-period EMA only from completed fifteen-minute candles.
- Build each fifteen-minute candle from three contiguous, completed, regular-session five-minute candles.
- Align fifteen-minute candles to regular-session boundaries beginning at 9:30 AM ET.
- If any source five-minute candle is missing, stale, or incomplete, do not create the fifteen-minute candle or evaluate the technical exit.

### Direction filter

- Calls are considered only when price is above VWAP.
- Puts are considered only when price is below VWAP.

### MACD confirmation

#### Calls

- MACD line is above the signal line.
- MACD histogram is positive.
- Current histogram value is greater than the prior histogram value.

#### Puts

- MACD line is below the signal line.
- MACD histogram is negative.
- Current histogram value is lower than the prior histogram value.

---

## 6. EMA-Bounce Entry Rules

### Call setup

1. The underlying is above session VWAP.
2. The bounce candle interacts with the 9 EMA.
3. The bounce candle closes above the 9 EMA.
4. The bounce candle is bullish.
5. MACD is bullish with a strengthening histogram.
6. The next five-minute candle opens above the 9 EMA.
7. The entry is evaluated after the confirming candle opens.

### Put setup

1. The underlying is below session VWAP.
2. The bounce candle interacts with the 9 EMA.
3. The bounce candle closes below the 9 EMA.
4. The bounce candle is bearish.
5. MACD is bearish with a strengthening histogram.
6. The next five-minute candle opens below the 9 EMA.
7. The entry is evaluated after the confirming candle opens.

### Invalidation

The setup is invalid if the next candle opens on the wrong side of the 9 EMA.

A canceled or expired entry requires a new qualifying EMA-bounce setup. The bot does not automatically retry the old setup.

---

## 7. Option Expiration Rules

### NVDA, TSLA, GOOGL, and AAPL

These symbols target short-dated weekly expirations listed on:

- Monday
- Wednesday
- Friday

Rules:

- Fetch the actual expiration list from Public.
- Select the nearest available listed expiration.
- Permit 0DTE.
- Do not generate expiration dates independently.
- Public's returned expiration list is authoritative.
- Display the selected expiration and DTE before entry.
- If the nearest expiration does not have a qualifying contract, the selector may evaluate the next available listed expiration.

Example display:

```text
NVDA / $200 / 07-29-2026 / CALL / WEEKLY
```

Example OSI-style symbol:

```text
NVDA260729C00200000
```

### SPY and QQQ

- Select the nearest available expiration returned by Public.
- Do not restrict SPY or QQQ to Monday, Wednesday, and Friday.
- Permit 0DTE.
- Display the exact expiration and DTE before entry.

---

## 8. Contract Selection

The underlying signal determines whether the bot searches calls or puts.

Approved filters:

- Target absolute delta: 0.45–0.60.
- Prefer ATM or one strike ITM.
- Maximum bid/ask spread: the lesser of:
  - $0.15, or
  - 10% of the midpoint.
- Minimum bid: $0.20.
- Minimum option volume: 100.
- Minimum open interest: 500.
- Reject zero-bid contracts.
- Use the exact option symbol returned by Public.
- Prefer the most liquid qualifying contract.

Ranking priority:

1. Correct nearest expiration.
2. Absolute delta between 0.45 and 0.60.
3. ATM or one strike ITM.
4. Spread within the approved maximum.
5. Highest volume.
6. Highest open interest.
7. Largest displayed bid/ask size.
8. Lowest spread percentage.

---

## 9. Buying-Power Allocation

The bot may use a maximum of **50% of available paper buying power**.

```text
Total strategy capacity = available buying power × 50%
Per-symbol capacity = total strategy capacity ÷ selected symbol count
```

| Selected symbols | Maximum allocation per selected symbol |
|---:|---:|
| 1 | 50.00% of buying power |
| 2 | 25.00% each |
| 3 | 16.67% each |
| 4 | 12.50% each |
| 5 | 10.00% each |
| 6 | 8.33% each |

The allocation is a maximum, not a target. Unused allocation remains uncommitted.

### Contract limit

- Maximum five contracts per position.
- Contract quantity is based on the option's maximum permitted entry price.
- Normal sizing must fit within that symbol's allocation.
- If normal sizing produces zero contracts, one contract may be allowed as an exception.
- The one-contract exception cannot breach the portfolio-wide 50% strategy ceiling.
- The paper account must have sufficient buying power.
- No averaging down.
- No adding to a position after entry.

### Capital reservation

Capital is reserved when an entry order is submitted.

```text
Reserved amount =
contracts × maximum permitted entry price × 100
```

The maximum permitted entry price is the highest price the entry algorithm is allowed to pay.

```text
Remaining strategy capacity =
50% strategy ceiling
− open-position cost
− pending-entry reservations
```

Changing the selected-symbol count affects future entries only. Existing positions are not resized.

---

## 10. Position and Order Restrictions

Approved rules:

- Only one active directional position per underlying.
- Calls and puts on the same underlying cannot coexist.
- A pending entry order occupies the symbol.
- Protective and profit-taking exit orders do not count as a second position.
- A symbol remains occupied until its position is flat and related orders are completed or canceled.
- Maximum two simultaneous positions.
- SPY and QQQ cannot both be open at the same time.
- No averaging down.
- No adding after entry.

---

## 11. Entry Order Workflow

All entries use limit orders.

```text
T+0 seconds   Submit at option midpoint
T+3 seconds   If unfilled, replace at midpoint plus one valid tick
T+6 seconds   If unfilled, replace up to the original ask
T+10 seconds  Cancel all remaining unfilled quantity
```

Additional rules:

- Never chase above the original ask by more than one valid tick.
- Cancel if the underlying setup becomes invalid.
- Cancel if the option spread exceeds the approved limit.
- Recalculate risk and buying power before each replacement.
- Partial fills become the final position size.
- Do not chase the unfilled remainder after ten seconds.
- A canceled entry requires a new setup.

---

## 12. Internal Paper Fill Model

The simulator must be conservative and must not assume automatic midpoint fills.

### Buy limit

A buy becomes marketable when:

```text
limit price >= current ask
```

When the buy limit is inside the spread, it remains working until a later ask reaches the limit.

### Sell limit

A sell becomes marketable when:

```text
limit price <= current bid
```

### Partial fills

- Use displayed ask size for buys when available.
- Use displayed bid size for sells when available.
- Maximum position size remains five contracts.
- If quote size is unavailable, do not assume unlimited liquidity.
- Partial fills are recorded as individual fill events.

### Stop fills

- Trigger the hard stop from the executable option bid.
- Fill from the next valid bid, subject to configured slippage.
- Do not assume an exact fill at the stop threshold.
- Losses may exceed 20% in a fast market.

### Stale data

No order, fill, stop, or P&L update may be processed from a stale quote.

Suggested initial stale thresholds:

- Underlying signal quote: 5 seconds.
- Option execution quote: 3 seconds.
- Five-minute candle: expected close time plus a small grace period.

---

## 13. Exit Rules

The first applicable rule closes or reduces the position.

### Hard stop

- Exit when the option's executable bid is 20% below the average option fill price.

```text
Hard stop = average option fill × 0.80
```

### Technical stop

- Calls exit when a completed fifteen-minute underlying candle closes below the fifteen-minute 9 EMA.
- Puts exit when a completed fifteen-minute underlying candle closes above the fifteen-minute 9 EMA.
- Evaluate the technical stop only after a valid fifteen-minute candle completes.
- The option-price hard stop, profit targets, break-even stop, 30-minute time stop, emergency exit, and 3:30 PM force-flat rule remain continuously active and may exit the position before a fifteen-minute candle completes.

### Time stop

- Maximum holding time is 30 minutes from the first fill.
- The timer does not reset after partial exits.

### End-of-day stop

- Force flat at 3:30 PM ET.
- Cancel every working order.
- The 3:30 PM rule overrides the 30-minute timer.

---

## 14. Scale-Out Ladder

Approved targets:

- Target 1: +30%
- Target 2: +50%
- Target 3: +75%
- Runner: exit on a completed fifteen-minute EMA violation, time stop, hard stop, or 3:30 PM force-flat

| Starting quantity | +30% | +50% | +75% | Runner |
|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 1 |
| 2 | 1 | 0 | 0 | 1 |
| 3 | 1 | 1 | 0 | 1 |
| 4 | 1 | 1 | 1 | 1 |
| 5 | 2 | 1 | 1 | 1 |

Targets are based on average entry price:

```text
Target 1 = average fill × 1.30
Target 2 = average fill × 1.50
Target 3 = average fill × 1.75
```

After Target 1:

- Move the remaining stop to break-even plus estimated round-trip fees.
- Keep the break-even stop continuously active; it does not wait for a fifteen-minute candle.
- Never move a stop in a way that increases risk.
- Profit targets and stops use executable option prices rather than an optimistic mark.

---

## 15. Daily Circuit Breakers

Approved controls:

- Maximum daily realized loss: 3% of starting account value.
- Maximum six entries per day.
- Maximum two entries per symbol per day.
- Stop trading after three consecutive losing trades.
- Fifteen-minute symbol cooldown after a stopped trade.
- No same-direction re-entry on the immediately following five-minute candle.
- Maximum two simultaneous positions.
- SPY and QQQ mutual exclusion.
- Emergency kill switch.

### Emergency kill switch

The kill switch:

1. Disables new entries.
2. Cancels pending entries.
3. Cancels working exit orders as necessary.
4. Closes all bot-managed positions.
5. Prevents further entries until manually reset.

---

## 16. Internal Paper Account

The paper account has a configurable starting balance.

Initial behavior:

- Cash-style long-options buying power.
- No simulated margin.
- Premium is deducted when a position fills.
- Sell proceeds return to cash when a position closes.
- Fees and slippage are configurable.
- Resetting the account creates a new ledger session rather than overwriting history.

Core calculations:

```text
Buying power =
cash
− pending-order reservations
− premium committed to open positions
+ closed-position proceeds
− fees
```

```text
Net account value =
cash
+ current liquidation value of open positions
```

---

## 17. P&L Calculations

The frontend must distinguish account-wide paper values from bot-only values.

### Mark P&L

For long options:

```text
mark = (bid + ask) ÷ 2

mark P&L =
(mark − average entry)
× open contracts
× 100
```

### Liquidation P&L

```text
liquidation P&L =
(current bid − average entry)
× open contracts
× 100
```

Risk rules use liquidation P&L.

### Realized P&L

```text
realized P&L =
sell proceeds
− allocated entry cost
− entry fees
− exit fees
```

### Daily P&L

```text
daily P&L =
today's realized P&L
+ current unrealized P&L
− today's fees
```

---

## 18. Frontend Requirements

The interface should resemble Webull's account, positions, orders, history, and performance workflow without copying proprietary assets.

### Persistent account summary

Show:

- Net account value.
- Available buying power.
- 50% bot allocation ceiling.
- Capital committed.
- Capital reserved.
- Remaining bot capacity.
- Open P&L.
- Daily P&L.
- Realized P&L.
- Bot status.
- Public market-data connection status.
- Current execution mode.

Source labels:

```text
Market Data: Public
Execution: Internal Paper
Mode: PAPER
Future Broker: Webull
```

### Main navigation

```text
Dashboard
Positions
Orders
Performance
Trade History
Strategy
Logs
Settings
```

---

## 19. Dashboard

The Dashboard includes:

- Account summary cards.
- Start bot.
- Pause new entries.
- Resume entries.
- Cancel all.
- Flatten all.
- Emergency stop.
- Selectable symbol toggles.
- Dynamic per-symbol allocation.
- Live signal status for every selected symbol.

Each symbol card shows:

- Underlying price.
- Above/below VWAP.
- 9 EMA relationship.
- MACD status.
- Selected expiration.
- Selected contract.
- Maximum affordable contracts.
- Signal state.
- Position state.
- Cooldown.
- Trades today.

---

## 20. Positions Page

The Positions page shows every open paper position.

Required fields:

- Underlying.
- Full option contract.
- Call or put.
- Expiration.
- DTE.
- Strike.
- Current quantity.
- Initial quantity.
- Average entry price.
- Current bid.
- Current ask.
- Mark.
- Total cost.
- Market value.
- Mark P&L.
- Liquidation P&L.
- Open P&L percentage.
- Daily P&L.
- Holding time.
- Current stop.
- Next target.
- Strategy state.
- Manual close action.

Clicking a position opens a detail panel containing:

- Entry rationale.
- Five-minute underlying chart.
- VWAP.
- 9 EMA.
- MACD.
- Entry and exit markers.
- Scale-out history.
- Stop movement history.
- Current spread.
- Public quote timestamps.
- Internal order IDs.
- Holding timer.
- Manual close control.

---

## 21. Orders Page

Subtabs:

```text
Working Orders
Filled Orders
Canceled Orders
Rejected Orders
All Today
```

Required order fields:

- Submitted time.
- Underlying.
- Contract.
- Side.
- Filled quantity / total quantity.
- Limit price.
- Stop price.
- Order type.
- Time in force.
- Status.
- Average fill.
- Filled time.
- Internal order ID.
- Future broker order ID field.
- Strategy reason.
- Cancel/inspect actions.

The detail view must show the complete order timeline, including:

- Initial midpoint submission.
- Each replacement.
- Partial fills.
- Cancellation.
- Rejection reason.
- Final state.

---

## 22. Trade History and Downloads

Filters:

- Today.
- This week.
- This month.
- Custom date range.
- Symbol.
- Calls or puts.
- Winning or losing trades.
- Paper or future live mode.
- Exit reason.
- Order status.

Completed-trade fields:

- Trade ID.
- Symbol.
- Contract.
- Direction.
- Entry time.
- Exit time.
- Holding time.
- Initial quantity.
- Average entry.
- Average exit.
- Gross P&L.
- Fees.
- Net P&L.
- Return percentage.
- Maximum favorable excursion.
- Maximum adverse excursion.
- Entry reason.
- Exit reason.
- DTE at entry.
- Result.

Download formats:

- CSV
- JSON

Download categories:

- Orders.
- Fills.
- Completed trades.
- Positions.
- Daily performance.
- Signal history.
- Full audit history.

Exports must include fill-level detail, not only one summarized row per trade.

---

## 23. Performance Page

Views:

```text
Account P&L
Bot P&L
Symbol P&L
Strategy P&L
```

Date ranges:

```text
Today
5D
1M
3M
6M
YTD
1Y
All
Custom
```

Metrics:

- Net P&L.
- Gross P&L.
- Realized P&L.
- Unrealized P&L.
- Fees.
- Win rate.
- Profit factor.
- Average winner.
- Average loser.
- Average holding time.
- Maximum drawdown.
- Largest win.
- Largest loss.
- Trade count.
- Consecutive wins.
- Consecutive losses.

Charts and summaries:

- Cumulative net P&L.
- Daily realized P&L.
- Drawdown.
- Gross versus net performance.
- P&L by symbol.
- Performance calendar.
- Bot trades versus manual trades when live integrations are added.

---

## 24. Strategy Page

Configurable strategy settings:

### Symbols

- Enabled/disabled.
- Expiration mode.
- Allow 0DTE.
- Maximum DTE.
- Maximum five contracts.
- Daily trade limit.
- Cooldown.

### Indicators

- VWAP enabled.
- EMA period: 9.
- MACD: 12/26/9.
- Strengthening histogram required.
- Completed five-minute candles.
- Next candle must open on the correct side of EMA.

### Risk

- Total buying-power allocation: 50%.
- Maximum five contracts.
- Hard premium stop: -20%.
- Maximum holding time: 30 minutes.
- Daily loss limit: -3%.
- Maximum six daily entries.
- Maximum two daily entries per symbol.
- Maximum two simultaneous positions.
- Stop after three consecutive losses.

### Scale-out

- +30%.
- +50%.
- +75%.
- Runner.

---

## 25. Logs and Audit Trail

The backend records every meaningful event:

- Market data received.
- Candle completed.
- Indicator calculated.
- Setup detected.
- Setup rejected.
- Contract selected.
- Risk check approved or rejected.
- Capital reserved.
- Order created.
- Order submitted.
- Order replaced.
- Order partially filled.
- Order filled.
- Order canceled.
- Stop moved.
- Target reached.
- Position closed.
- Public connection lost.
- Quote became stale.
- Circuit breaker triggered.
- Emergency action.

Logs are searchable and downloadable.

---

## 26. Ledger and Database

Recommended core tables:

```text
paper_accounts
account_snapshots
orders
order_events
fills
positions
position_lots
cash_transactions
strategy_signals
risk_decisions
market_snapshots
daily_performance
system_events
```

Order event states:

```text
CREATED
RESERVED
SUBMITTED
WORKING
PARTIALLY_FILLED
REPLACED
FILLED
CANCEL_REQUESTED
CANCELED
REJECTED
EXPIRED
```

Cash event types:

```text
INITIAL_DEPOSIT
BUY_PREMIUM
SELL_PROCEEDS
COMMISSION
REGULATORY_FEE
ADJUSTMENT
RESET
```

P&L and account balances must be reproducible from fills and cash events.

---

## 27. Broker-Neutral Interfaces

```python
from typing import Protocol


class MarketDataProvider(Protocol):
    async def get_bars(self, symbol: str, timeframe: str):
        ...

    async def get_quote(self, symbol: str):
        ...

    async def get_option_expirations(self, symbol: str):
        ...

    async def get_option_chain(self, symbol: str, expiration: str):
        ...

    async def get_option_quotes(self, option_symbols: list[str]):
        ...


class ExecutionBroker(Protocol):
    async def get_account(self):
        ...

    async def submit_order(self, order):
        ...

    async def replace_order(self, order_id: str, replacement):
        ...

    async def cancel_order(self, order_id: str):
        ...

    async def get_order(self, order_id: str):
        ...

    async def list_positions(self):
        ...

    async def flatten_all(self):
        ...
```

The strategy engine must not contain Public-, Alpaca-, or Webull-specific execution logic.

---

## 28. Development Sequence

```text
Phase 1
Public market data + internal paper broker + PostgreSQL ledger

Phase 2
React dashboard, positions, orders, history, downloads, and performance

Phase 3
Live paper operation during market hours

Phase 4
Validate fill quality, slippage, stops, scale-outs, and P&L calculations

Phase 5
Optional Alpaca paper comparison adapter

Phase 6
Webull broker adapter after API approval

Phase 7
Webull shadow mode and order-preview comparison

Phase 8
Webull live approval mode

Phase 9
Optional fully automated Webull execution
```

---

## 29. Safety Requirements

- Paper mode is the only enabled mode in Version 1.
- The frontend must always show the current market-data and execution sources.
- Stale data disables entry and exit simulation until valid data returns.
- Every automated decision must be auditable.
- The 50% strategy ceiling is portfolio-wide.
- The 3:30 PM force-flat rule cannot be disabled during normal operation.
- The emergency kill switch must be available from every primary page.
- Manual position closure must remain available.
- No secret keys may be stored in source control.

---

## 30. Items Still Configurable Before Implementation

These values were not permanently fixed and should be environment or settings values:

- Initial paper-account balance.
- Simulated commission schedule.
- Simulated regulatory fees.
- Slippage amount.
- Behavior when displayed option size is unavailable.
- Public API credentials.
- Database connection settings.
- Deployment environment.
- Webull integration timing.
- Whether Alpaca comparison mode is implemented.

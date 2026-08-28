# Manual Desk — Full Plan (tracker + order entry + options search)

The human-driven surface: search everything Alpaca exposes on an option, submit
orders (single and multi-leg), and track positions/orders/P&L live. No agent.

## Build vs adopt — decision

**Build on `frontend/` (already in this repo). Do not adopt a large OSS dashboard.**

| Option | Verdict |
|---|---|
| Extend our `frontend/` (FastAPI + vanilla JS) | **Chosen.** Lean, ours to demo, fits the crypto-proxy thesis, scores on Technology Implementation |
| [rcland12/alpaca-ui](https://github.com/rcland12/alpaca-ui) | Strong reference (stock+options, charts, paper/live) — borrow ideas, not code |
| [zaldabenld/alpaca-paper-trader](https://github.com/zaldabenld/alpaca-paper-trader) | Python/FastAPI desktop; good pattern reference |

Importing a general dashboard weakens the "originality" and "implementation"
criteria and hides the thesis. We keep our surface small and purpose-built.

## What Alpaca gives us (options data layer)

| Data | Source (alpaca-py) | Notes |
|---|---|---|
| Account, equity, options BP, level | `TradingClient.get_account()` | daily P&L = equity − last_equity |
| Positions + unrealized P&L | `get_all_positions()` | includes option legs |
| Open orders / history | `get_orders()` | filter by status |
| Activities (fills, realized P&L) | `get_account_activities()` | the audit feed |
| Contract list + **open interest** + strike/expiry | `get_option_contracts()` | OI lives here |
| Live **quote, greeks (Δ Θ Γ ν ρ), IV, last trade** | `OptionHistoricalDataClient` snapshot / chain | **live snapshot only, no history** |

> **Two-call pattern:** the chain snapshot gives bid/ask + greeks + IV but **not**
> open interest; `get_option_contracts()` gives OI + strike/expiry but not greeks.
> The desk joins them per contract. (Confirmed in Alpaca docs.)

## Features

### 1. Search everything on an option
- Underlying input (default universe: MSTR COIN CRCL MARA RIOT IBIT)
- Calls / puts / both
- Full chain: strike, expiry, bid/ask, last, **Δ Θ Γ ν**, **IV**, **OI**, volume
- Filters: DTE window, moneyness (± % of spot), min OI, max bid/ask spread,
  delta band (e.g. 0.15–0.35 for premium selling)
- Sort by any column; highlight the ATM row

### 2. Order entry
- **Single-leg:** buy/sell, qty, market or limit, TIF
- **Multi-leg (spreads):** build 2–4 legs, net debit/credit preview, submit as one
  order via Alpaca's multi-leg support (Level 3 — you have it)
- **Preview before submit:** max profit, max loss, breakeven, buying-power effect
- **Optional risk check:** run the agent's `risk.py` gates as *warnings* (not blocks)
  so the manual desk and the agent share one risk definition

### 3. Tracker
- Positions with per-leg unrealized P&L and aggregate greeks
- Open orders (cancel button)
- Order history + realized P&L from activities
- Account P&L header, live (15s poll; upgrade to websocket later)

## Backend routes (extends frontend/server.py)

```
GET  /api/account              equity, cash, options BP/level, daily P&L
GET  /api/positions            open positions + unrealized P&L
GET  /api/orders?status=open   open / all orders
POST /api/orders/{id}/cancel   cancel an order
GET  /api/activities           fills + realized P&L
GET  /api/chain?symbol=&kind=  chain JOINED with greeks/IV/OI  [enrich existing]
GET  /api/snapshot?symbol=     single-contract live quote+greeks+IV
POST /api/order                single-leg  [exists]
POST /api/order/multileg       spread / multi-leg  [new]
POST /api/preview              max P/L, breakeven, BP effect (no order placed)
```

## Build order

1. **Enrich the chain** — join `get_option_contracts` (OI) with the snapshot
   (greeks/IV). This is the "search everything" core. *(half day)*
2. **Orders + activities tracker** — open orders w/ cancel, history, realized P&L.
3. **Order preview** — max P/L, breakeven, BP effect before submit.
4. **Multi-leg ticket** — build spreads, net credit/debit, submit as one order.
5. **Shared risk warnings** — surface `risk.py` verdicts inline.
6. **Polish** — ATM highlight, filters, delta band, websocket live quotes.

## Guardrail

This surface is **manual** — a human confirms every order. The agent's risk gate
is reused here only as *advice*. Nothing here trades on its own; autonomy lives in
the separate agent build.

# Glaz Manual Desk — human-driven options trading

No agent. You pick the trade; keys stay server-side. This is the "try it by
hand" surface, separate from the autonomous agent.

## Run

```bash
uv run python -m frontend.server
# open http://127.0.0.1:8000
```

## What it does

- **Account** — equity, daily P&L, options level, live (15s refresh)
- **Positions** — open positions with unrealized P&L
- **Option chain** — enter an underlying (MSTR / COIN / CRCL / MARA / RIOT / IBIT),
  calls or puts, 7–45 DTE window; click a row to load it into the ticket
- **Order ticket** — buy/sell, qty, market or limit → places on your paper account

Everything hits Alpaca's **paper** API directly via `alpaca-py`. The browser never
sees your keys — the FastAPI backend holds them and proxies each call.

## Two ways to trade manually

| Path | How |
|---|---|
| **This dashboard** | click trades in the browser |
| **MCP in Claude Code** | tell Claude "buy 1 MSTR 400 call" — it places it via the Alpaca MCP tools |

Both are manual (human-directed). The autonomous agent is a separate, later build.

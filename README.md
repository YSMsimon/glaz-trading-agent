# Glaz — Autonomous Options Trading Agent

Built for the **Alpaca AI Trading Agents Hackathon** (lablab.ai × Alpaca, Aug 28–Sep 4 2026).

An autonomous agent that trades **US equity options** on Alpaca's paper environment
through the **MCP server** and **CLI**, under hard risk gates. Judged on live P&L.

## What it does

- Reads the options chain and selects defined, testable strategies (spreads, multi-leg)
- Executes autonomously via Alpaca's Trading API / MCP / CLI
- Enforces risk gates before every order — see `agent/config.py`

## Risk gates

| Gate | Default | Why |
|---|---|---|
| Max position size | 5% of equity | no single trade can sink the book |
| Daily loss halt | −3% | agent stops trading for the day |
| Max open positions | 10 | bounded exposure |
| DTE window | 7–45 days | avoids gamma-heavy weeklies |

Sizing is measured against **equity, not buying power** — the paper account shows
4× margin, which is not a spending limit.

## Setup

```bash
uv sync
cp .env.example .env      # paste Alpaca paper keys
uv run python -m agent.smoke_test
```

## Stack

Alpaca Trading API · MCP server · Alpaca CLI · alpaca-py · paper environment.

## License

MIT

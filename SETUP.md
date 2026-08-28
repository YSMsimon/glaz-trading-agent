# Setup — Alpaca AI Trading Agents Hackathon

**Deadline: 2026-09-04, 11:00 EDT.**

## Already done for you

| | |
|---|---|
| `uv` 0.12.7 | Homebrew |
| Alpaca CLI 0.0.13 | `~/.local/bin/alpaca` (already on PATH) |
| `alpaca-mcp-server` | `uv tool install` |
| `alpaca-py` + deps | project venv, `uv sync` |
| Project scaffold | `agent/config.py`, `agent/smoke_test.py`, `.gitignore` |

The Homebrew tap for the CLI needs Xcode Command Line Tools, so the prebuilt
`darwin_arm64` binary was used instead. Same thing, no compiler needed.

## Your four steps

### 1. Create the paper account — you must do this yourself

https://app.alpaca.markets/paper/dashboard/overview

I can't create accounts or handle passwords. Sign up, then come back.

> **Make it a fresh account.** The rules disqualify projects run on a reused
> account. If you already have an Alpaca account, create a *new* paper account
> dedicated to this hackathon.

### 2. Set balance to $100,000 and enable options

Both in the paper dashboard:

- **Reset** the account, set starting balance to exactly `100000`
- **Request options approval.** Every strategy must use options — without
  approval nothing you build can trade.

### 3. Paste your keys

    cd ~/Desktop/alpaca-agent
    cp .env.example .env
    # open .env, paste ALPACA_API_KEY and ALPACA_SECRET_KEY from the dashboard

`.env` is gitignored. Never commit it, never paste keys into a chat.

### 4. Verify

    uv run python -m agent.smoke_test

Prints equity, options level, and your account id. It warns if equity isn't
$100,000 or options aren't enabled. **Save the account id** — the submission
requires it.

## Then: connect the MCP server

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "paste_here",
        "ALPACA_SECRET_KEY": "paste_here",
        "ALPACA_PAPER_TRADE": "true"
      }
    }
  }
}
```

Options tools it exposes: `get_option_contracts`, `get_option_chain`,
`get_option_snapshot`, `place_option_order` (single and multi-leg),
`exercise_options_position`.

## CLI quick reference

    alpaca profile login                              # OAuth, paper by default
    alpaca account get
    alpaca option contracts --underlying-symbol AAPL
    alpaca data option chain --underlying-symbol AAPL
    alpaca option get --symbol-or-id AAPL260918C00250000

## Submission checklist

- [ ] Public GitHub repo
- [ ] Demo app + URL
- [ ] **Alpaca paper account id** (fresh account)
- [ ] Cover image, video, slides
- [ ] One-page write-up: AI logic, **risk gates**, Alpaca infrastructure
- [ ] Up to 5 social posts tagging @lablabai and @AlpacaHQ
- [ ] Register on lablab.ai **and** Discord

## Two things worth knowing

**Risk gates are a named judging input.** `agent/config.py` already has
placeholders — position cap, daily loss halt, DTE bounds. Filling those in
thoughtfully is cheap points, and most submissions won't bother.

**Social is scored.** Up to 5 posts, judged on quality *and* engagement. Two
teams win $500 for it alone. Starting posts on day one beats backfilling on day six.

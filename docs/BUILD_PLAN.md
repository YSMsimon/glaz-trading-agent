# Build Plan — 7 Days

Kickoff Aug 28, submission **Sep 4 11:00 EDT**. Ordered so a working, submittable
agent exists early and every later day improves it — never "nothing works until day 6".

## Day 1 — foundation (today)
- [ ] API secret into `.env`; `uv run python -m agent.smoke_test` passes
- [ ] Connect Alpaca MCP server to Claude (config in SETUP.md)
- [ ] `agent/data.py` — pull account snapshot + option chain for one ticker (MSTR)
- [ ] **First social post** — "building an options agent on crypto-proxy equities"
- [ ] Confirm CRCL / COIN / MSTR chains are liquid enough to trade

## Day 2 — the risk gate (pure code, no model)
- [ ] `agent/risk.py` — position-size cap, daily-loss halt, DTE window, defined-risk-only
- [ ] Unit tests for every gate (evals-first: the gate is what must never fail)
- [ ] `data/state.json` + `data/journal.jsonl` read/write

## Day 3 — the decision loop
- [ ] `agent/decide.py` — Claude call with the append-only context (DESIGN.md)
- [ ] IV-regime → structure selection (STRATEGY.md)
- [ ] Wire observe → decide → gate → execute → record end to end on paper
- [ ] Second social post (a real trade + its rationale)

## Day 4 — run it live + harden
- [ ] Schedule the loop across a market session on PA38RM7WNFDD
- [ ] Handle market-closed, no-fill, partial-fill, halt-triggered
- [ ] Optional: Featherless model for IV-regime label (partner-prize eligibility)

## Day 5 — let P&L accumulate + presentation
- [ ] Agent trading; watch journal + P&L
- [ ] Record the demo video (agent observing → reasoning → gating → trading)
- [ ] Third/fourth social posts

## Day 6 — write-up + slides
- [ ] One-pager: AI logic, **risk gates**, Alpaca infrastructure (a judged deliverable)
- [ ] Slides; polish README; a P&L / decision chart from journal.jsonl
- [ ] Fifth social post (results-so-far)

## Day 7 — submit (do NOT wait for the deadline)
- [ ] Final: repo public + MIT, video, slides, cover image
- [ ] **Account ID `PA38RM7WNFDD`** in the form — this is how they read P&L
- [ ] Up to 5 social links tagging @lablabai + @AlpacaHQ
- [ ] Registered on lablab.ai AND Discord
- [ ] Submit with hours to spare

## Standing rule
The agent must be running on the paper account during the window. **P&L is read from
the account, not simulated** — no live trades, no P&L to judge.

# Agent Build Plan — "Claude-as-agent" over MCP

The agent is **not a standalone program**. It is Claude (or Codex) reasoning
natively, using the **Alpaca MCP** as hands, guided by **skill files**, and
constrained by a **deterministic risk gate**. You chat; the model trades.

Why this shape (your call, and the right one):
- **Fewer tools → better reasoning.** A big custom tool-graph makes the model
  worse. Give it the MCP + a risk check and nothing else.
- **No hand-rolled decision loop.** The reasoning *is* the model's. We don't
  re-implement thinking in Python.
- **Skills as files.** Strategy lives in versioned markdown the model reads, not
  in code. Editing the playbook = editing a file, not a rewrite.
- Matches how you already design agents: split by responsibility, skills as
  files, memory that survives the session, evals first.

## Architecture — 5 thin layers

```
  YOU (chat)
     │
  ┌──▼─────────────────────────────────────────────┐
  │ REASONING   = Claude / Codex (native, no loop)  │  ← decides
  ├─────────────────────────────────────────────────┤
  │ SKILLS      = skills/*.md (playbook, read-only)  │  ← how to decide
  ├─────────────────────────────────────────────────┤
  │ RISK        = agent/risk.py (deterministic gate) │  ← veto, can't be argued
  ├─────────────────────────────────────────────────┤
  │ EXECUTION   = Alpaca MCP  (chain, order, close)  │  ← hands
  ├─────────────────────────────────────────────────┤
  │ MEMORY      = journal.jsonl + state.json         │  ← what persists + audit
  └─────────────────────────────────────────────────┘
```

Each layer is replaceable and testable alone. The model is the only "smart"
part; everything else is a file or a pure function.

## Do we need subagents?

**v1: no.** One reasoning context trades better than many. Subagents fragment
context and you explicitly want strong single-model reasoning. A trading decision
needs the *whole* picture (positions + chain + risk + journal) in one head.

**v2 (optional, one only): an adversarial risk-verifier.** Before a live entry,
spawn ONE subagent whose sole job is to *refute* the trade ("why is this bad?").
If it finds a real objection, the entry pauses. This is the single place a second
context adds value — independent skepticism on irreversible actions. Add it only
after v1 works. Nothing else warrants a subagent.

**Never:** a subagent per indicator, per ticker, per step. That's tool-sprawl in
disguise and it degrades reasoning.

## The MCP toolset — keep it small on purpose

Use only these Alpaca MCP tools. More than this hurts.

| Need | MCP tool |
|---|---|
| See the account | `get_account`, `get_positions` |
| Find contracts | `get_option_contracts`, `get_option_chain` |
| Price a contract | `get_option_snapshot` |
| Trade | `place_option_order` (single + multi-leg) |
| Manage | `get_orders`, `cancel_order`, `close_position` |

**Do not** wire in news scrapers, dozens of indicators, or auto-charting tools.
The edge is disciplined mechanics, not more inputs.

## Orchestration — three ways to run the same agent

- **A · Interactive (build this first).** You chat with Claude here; Claude reads
  `skills/`, checks `risk.py`, trades via MCP, writes the journal. Human-in-loop.
  This is "you still chat with me and I use the MCP to trade."
- **B · Scheduled (autonomy for the competition).** A cron/loop re-invokes Claude
  every N minutes with a fixed prompt: "load skills + state, scan the universe,
  act within risk gates, journal." Same skills, no human. This is what generates
  the judged P&L.
- **C · Codex / other client.** Same skills + same MCP; swap the reasoning model.
  Nothing in the design is Claude-specific except the wrapper prompt.

## Build steps (each ships something usable)

1. **Skills layer** — write `skills/*.md` (done in this commit). The playbook is
   the product; get it right first.  ✅ acceptance: a human could trade from it.
2. **Session bootstrap** — `AGENT_SESSION.md`: the standing prompt that starts
   every session ("read skills, summarize state, propose actions").
3. **Risk as a callable** — expose `risk.py` so the model runs every proposed
   trade through it before ordering (CLI: `uv run python -m agent.riskcheck ...`).
4. **Journaling discipline** — every decision + fill appended to `journal.jsonl`
   with its rationale. This is memory AND the hackathon audit trail.
5. **Interactive mode live** — restart Claude (MCP picks up keys), trade a paper
   spread by chat, confirm it journaled.  ✅ acceptance: one real logged trade.
6. **Scheduled mode** — wrap the session prompt in a loop/cron for the compe­tition
   window.  ✅ acceptance: unattended for one session, journal fills, risk holds.
7. **(Optional) v2 verifier subagent** — adversarial refute-check before entries.

## Best option-trading abilities (encoded in skills/)

The edge on high-IV crypto proxies is **selling premium with defined risk** when
IV is rich, and **buying debit spreads** on conviction when it's cheap. Full
mechanics — entry filters, profit targets, stops, roll/exit, sizing — live in
`skills/strategy-selection.md` and `skills/entry-exit-rules.md`. Summary:

| Regime (IV rank) | Structure | Why |
|---|---|---|
| High (≥ 50) | short put spread / iron condor | harvest rich premium, defined risk |
| Directional + high IV | short spread in trend direction | premium + a directional tilt |
| Low (< 30) + conviction | long debit spread | cheap optionality, capped cost |
| No edge | **no trade** | flat is a position |

Discipline (not prediction) is the edge: mechanical entries, 50% profit-take,
2× stop, time-exit at 21 DTE, 5%-equity sizing, defined-risk only.

## Evals — prove it before trusting it

- **Risk gate tests** (exist, 8 passing) — the gate must never pass a bad trade.
- **Dry-run** — the model proposes trades on live data but writes them to the
  journal WITHOUT ordering; you read the journal and judge the decisions.
- **Paper metrics** — win rate, avg P&L per trade, max drawdown, gate-rejections.

## How this satisfies the hackathon

- **Autonomous agent** — scheduled mode trades unattended. ✓
- **MCP + CLI** — trades via Alpaca MCP; risk check via CLI. ✓
- **Options** — every strategy is an options structure. ✓
- **P&L** — read from account `PA38RM7WNFDD`. ✓
- **Write-up** — this doc + skills + journal ARE the write-up: AI logic, risk
  gates, Alpaca infra, all documented and versioned. ✓

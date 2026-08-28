# Design — Agent Architecture

Two principles drive the whole design:
**(1) earlier context is never mutated**, so the model's prompt cache stays valid
across cycles; **(2) durable state lives in files**, so the agent survives restarts
and leaves an audit trail a judge can read.

## Context is append-only (cache-friendly)

Anthropic prompt caching only reuses a prefix that is **byte-identical** to the last
call. So the prompt is built in two zones:

```
┌─ STATIC PREFIX ───────────────────────────  [cache-read every cycle]
│  system prompt: role, strategy rules, risk constraints
│  tool schemas (MCP / CLI wrappers)
│  strategy skill files (docs/STRATEGY.md, loaded read-only)
│  ← cache_control breakpoint here
├─ APPEND-ONLY LEDGER ──────────────────────  [grows; never edited]
│  t0  portfolio snapshot (cash, positions, buying power)
│  t0  decision + rationale
│  t1  fill confirmations
│  t1  new snapshot
│  ...
└───────────────────────────────────────────
```

Rules:
- The static prefix is assembled once and **never changes within a run-series**.
  Editing it (even a whitespace tweak) invalidates the cache — so it's frozen.
- Every cycle **appends**: new observation, new decision, new fill. It never rewrites
  a prior turn. Old entries are immutable history.
- Result: each cycle is a **cache read** of everything before + a small **cache write**
  of the new tail. Cost and latency scale with the new tokens, not the whole history.

This is the "no changing of earlier context for cache read/write" requirement made
concrete.

## Durable state lives in files

| File | Role | Shape |
|---|---|---|
| `data/state.json` | current truth | positions, realized daily P&L, halt flag, strategy state |
| `data/journal.jsonl` | append-only memory + audit trail | one line per observation / decision / fill, timestamped |

On startup the agent reloads `state.json` and replays a summary of `journal.jsonl`
to rebuild the append-only ledger. **Persistence without mutation**: history is
replayed, never rewritten. The journal doubles as the evidence a judge (or you)
reads to see *why* each trade happened.

## Layers, separated by responsibility

```
  observe  →  decide  →  gate  →  execute  →  record
   (data)     (model)   (code)    (MCP/CLI)   (files)
```

- **observe** — pull account + option-chain snapshots (Alpaca data API / MCP tools)
- **decide** — the model proposes an action + rationale. Reasoning only; no side effects.
- **gate** — `agent/risk.py`, **pure code, no model.** Rejects anything breaching a
  risk gate. A model can hallucinate; a gate cannot be argued with. This is the
  safety boundary and it is deterministic.
- **execute** — place the order via Alpaca MCP `place_option_order` or the CLI
- **record** — append the outcome to `state.json` + `journal.jsonl`

The gate being non-model is the point: **the LLM decides, code vetoes.**

## Models

- **Reasoning model:** Claude via the Anthropic API — the decision layer.
- **Optional second model:** Featherless AI (open-source inference, $25 hackathon
  credit) for a cheap sub-task — e.g. IV-regime label or headline sentiment.
  Integrating Featherless also makes the project eligible for the **partner prize**.

Keep the split by *responsibility*, not novelty: use a second model only where a
cheaper/faster call genuinely fits. One good model beats two bolted together.


### Locked-in split (implemented)

| Concern | Model | Module |
|---|---|---|
| Trade decisions, sizing, structure | **Claude** (Anthropic API) | `agent/decide.py` |
| Volatility-regime label (HIGH/NORMAL/LOW) | **Featherless** (`Qwen2.5-7B-Instruct`) | `agent/regime.py` |

`regime.py` is a bounded classifier: it answers one question and returns a JSON
label, nothing more. It has a **deterministic rule fallback**, so a Featherless
outage or a bad response never blocks a trading cycle — the partner model is an
enhancement, not a dependency. Claude consumes the regime label as one input and
makes the actual call.

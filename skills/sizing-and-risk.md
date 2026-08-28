# Sizing & Risk — the deterministic floor

The model proposes; `agent/risk.py` decides. These match the code so there's one
definition of risk.

| Gate | Limit |
|---|---|
| Max loss per position | ≤ **5%** of equity |
| Daily loss halt | **−3%** of equity → no new risk |
| Max open positions | **10** |
| DTE window | **7–45** |
| Naked short options | **forbidden** |

## Sizing method
1. Compute the structure's **max loss** (width − credit, ×100, ×contracts).
2. contracts = floor( 0.05 × equity ÷ max_loss_per_contract ).
3. If contracts < 1, the trade is too big — skip.
4. Size against **equity, not buying power.** Buying power is 4× on paper; using
   it as a budget is how you blow up.

## Before every order
LIMIT orders only on spreads (see entry-exit-rules). Run: `uv run python -m agent.riskcheck --contracts N --price P --dte D
--defined true` (or the equivalent). If it returns warnings, revise — never
override.

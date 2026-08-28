# Entry & Exit — mechanical, non-negotiable

## Entry filters (ALL must pass)
- DTE between **7 and 45** (sweet spot 30–45 for premium selling)
- Structure matches the IV regime (`strategy-selection.md`)
- Passes the liquidity gate (`universe.md`)
- Passes the risk gate (`agent/risk.py`) with **zero** warnings
- Not already holding the same structure on that underlying

## Exits (whichever comes first)
- **Profit target:** close at **50%** of max profit (credit spreads) / **50%**
  gain (debit spreads). Take it — don't get greedy.
- **Stop:** close if loss reaches **2×** the credit received (credit) or **50%**
  of debit paid (debit).
- **Time stop:** close/roll at **21 DTE** regardless — gamma risk rises fast
  inside three weeks.
- **Halt override:** if the daily −3% halt trips, manage/close only.

## Rolling
Roll a tested short spread out in time only if IV is still elevated AND it can be
rolled for a credit. Otherwise close and move on. Never roll a loser for a debit.

## Execution — LIMIT orders only on spreads (hard rule, learned 2026-08-28)
NEVER submit a multi-leg spread as a market order. Market orders fill each leg at
the worst side (sell shorts at bid, buy wings at ask), giving up the entire
bid/ask on every leg — on a 2-leg spread that can be $100–400 of pure slippage,
and on wide OTM wings the fill can be nonsensical (a further-OTM wing filling
above the nearer short). Always submit the combo as a LIMIT at the net credit
(start at mid; if unfilled, improve by a nickel toward the natural price). A
spread that won't fill at a fair limit is a spread not worth doing.

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

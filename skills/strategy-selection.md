# Strategy Selection — regime drives structure

First compute the **IV rank** (where current IV sits in its own 1-year range).
Then pick the structure. Never pick a structure first and justify it after.

| IV rank | Bias | Structure | Notes |
|---|---|---|---|
| ≥ 50 | neutral | **iron condor** | sell both sides, defined risk, harvest premium |
| ≥ 50 | bullish | **short put spread** (bull put) | premium + upward tilt |
| ≥ 50 | bearish | **short call spread** (bear call) | premium + downward tilt |
| 30–50 | directional | **debit spread** in the trend | cheaper, directional |
| < 30 | strong conviction | **long debit spread** | cheap optionality, capped cost |
| any | no clear edge | **no trade** | the default |

## Structure specs
- **Short put spread:** sell ~0.30Δ put, buy ~0.15Δ put below. Credit ≥ 1/3 of
  width. Width sized so max loss ≤ 5% equity.
- **Iron condor:** short strikes ~0.20Δ each side, wings ~0.10Δ. Symmetric width.
- **Debit spread:** buy ~0.50Δ, sell ~0.25Δ in the direction of conviction.

All strikes chosen from the liquidity-gated chain (`universe.md`).

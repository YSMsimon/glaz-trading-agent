# Strategy — Crypto Exposure, Equity-Options Mechanics

## Thesis

Crypto options aren't available on Alpaca. Crypto-**proxy equities** are, with deep,
liquid options chains. The agent trades options on the names whose price is driven
by crypto, capturing the theme while staying 100% inside the hackathon's
equity-options requirement.

## Universe

| Ticker | Company | Why |
|---|---|---|
| MSTR | Strategy (MicroStrategy) | Largest corporate BTC holder; option chain is one of the most liquid in the market |
| COIN | Coinbase | Exchange revenue = crypto beta |
| CRCL | Circle | USDC issuer — direct stablecoin proxy. Verify chain liquidity at build time (2026 IPO) |
| MARA | MARA Holdings | BTC miner, very high IV |
| RIOT | Riot Platforms | BTC miner, very high IV |
| IBIT | iShares Bitcoin Trust ETF | Cleanest spot-BTC proxy with listed options |

Selection at runtime is liquidity-gated: only trade a contract if open interest and
bid/ask spread clear a threshold. Illiquid strikes are skipped, logged, not traded.

## Why options, not shares

These names carry **elevated implied volatility** (crypto beta). High IV makes option
premium rich — which is an edge you can harvest with *defined-risk* structures instead
of betting on direction.

## Strategy selection — IV regime drives structure

| Regime | Signal | Structure |
|---|---|---|
| High IV rank | IV percentile high vs. its own history | **Sell** premium: credit spreads, iron condors (defined risk) |
| Directional conviction | trend / momentum signal | **Buy** debit spreads (capped cost) |
| No edge | neither fires | **No trade.** Flat is a position. |

**Defined-risk only.** No naked short options — every position has a known max loss,
which is what lets the risk gates size it. This is a deliberate judgment signal, not a
limitation.

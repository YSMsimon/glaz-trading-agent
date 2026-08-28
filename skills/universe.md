# Universe — what you may trade

Only options on these crypto-proxy US equities/ETFs. Crypto itself has no options
on Alpaca; these give crypto beta with a real options chain.

| Group | Tickers |
|---|---|
| Proxy / treasury | MSTR, BMNR, SBET |
| Exchanges / brokers | COIN, HOOD, GLXY, CRCL |
| Miners / data-center | MARA, RIOT, CLSK, CIFR, WULF, IREN, CORZ, HUT, BITF, BTDR, APLD, HIVE |
| ETFs | IBIT, FBTC, BITO, GBTC, BITX |

## Liquidity gate (hard)
Trade a contract only if ALL hold:
- open interest ≥ 100
- bid/ask spread ≤ 15% of the mid
- the underlying is one of the above

Skip and journal anything that fails. Illiquid options are how paper accounts
quietly bleed to the spread.

## Preference
MSTR, COIN, IBIT have the deepest chains — prefer them when several names give a
similar setup. Miners are highest IV (richest premium) but widest spreads — only
when liquidity gate passes.

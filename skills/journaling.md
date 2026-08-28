# Journaling — memory + audit trail

Every decision appends one JSON line to `journal.jsonl`. This is how the agent
remembers across sessions AND how a judge (or you) sees *why* each trade happened.

## Append on: entry, exit, no-trade, and halt.
```json
{"ts":"<passed-in>","action":"entry|exit|no_trade|halt",
 "underlying":"MSTR","structure":"short_put_spread",
 "legs":["MSTR260918P00120000 sell","MSTR260918P00110000 buy"],
 "iv_rank":62,"dte":24,"credit":1.85,"max_loss":315,"contracts":1,
 "risk_ok":true,"rationale":"IV rank 62, bullish tilt, 0.30Δ short put, defined",
 "order_id":"...","result":null}
```

## Rules
- Journal the **reason**, not just the trade. A no-trade with "IV rank 22, no
  edge" is as valuable as an entry.
- On exit, fill `result` with realized P&L and which exit rule fired.
- Never edit a past line. Append only. History is immutable.

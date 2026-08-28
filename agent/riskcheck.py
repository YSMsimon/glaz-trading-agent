"""CLI wrapper around the risk gate, so the reasoning model (Claude/Codex) can
run a proposed trade through deterministic checks before ordering.

    uv run python -m agent.riskcheck --contracts 1 --price 3.15 --dte 24 \
        --equity 100000 --open 2 --daily-pl 0 --defined true
"""
from __future__ import annotations
import argparse, json
from agent import risk

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contracts", type=int, required=True)
    ap.add_argument("--price", type=float, required=True,
                    help="max loss per contract / 100 (premium-per-share basis)")
    ap.add_argument("--dte", type=int, required=True)
    ap.add_argument("--equity", type=float, default=100_000)
    ap.add_argument("--open", type=int, default=0, dest="open_positions")
    ap.add_argument("--daily-pl", type=float, default=0.0)
    ap.add_argument("--defined", default="true")
    a = ap.parse_args()
    v = risk.check_order(
        contracts=a.contracts, contract_price=a.price,
        kind_is_defined_risk=(a.defined.lower() == "true"),
        dte=a.dte, equity=a.equity, open_positions=a.open_positions,
        daily_pl=a.daily_pl)
    print(json.dumps({"ok": v.ok, "warnings": v.warnings}, indent=2))
    raise SystemExit(0 if v.ok else 1)

if __name__ == "__main__":
    main()

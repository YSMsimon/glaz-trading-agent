"""Pure options math — no network, no keys. Used by the desk's order preview
and testable in isolation. All prices are per-share; options are x100."""
from __future__ import annotations
from dataclasses import dataclass

MULT = 100  # US equity option contract multiplier


@dataclass
class Leg:
    side: str        # "buy" | "sell"
    kind: str        # "call" | "put"
    strike: float
    price: float     # premium per share
    qty: int = 1


@dataclass
class Payoff:
    max_profit: float | None   # None = unlimited
    max_loss: float | None     # None = unlimited (naked short)
    breakevens: list[float]
    net: float                 # + = credit received, - = debit paid


def _intrinsic(kind: str, strike: float, spot: float) -> float:
    return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)


def value_at(legs: list[Leg], spot: float) -> float:
    """P/L in dollars at a given underlying price at expiry."""
    total = 0.0
    for lg in legs:
        intr = _intrinsic(lg.kind, lg.strike, spot)
        sign = 1 if lg.side == "buy" else -1
        # cost basis: buy pays premium, sell receives it
        total += sign * (intr - lg.price) * MULT * lg.qty
    return total


def analyze(legs: list[Leg]) -> Payoff:
    """Max profit/loss + breakevens for single legs and verticals.
    Scans a strike grid — robust for any defined-risk combo."""
    net = sum((lg.price * MULT * lg.qty) * (1 if lg.side == "sell" else -1) for lg in legs)
    strikes = sorted({lg.strike for lg in legs})
    lo, hi = strikes[0] * 0.2, strikes[-1] * 2.0
    grid = [lo + (hi - lo) * i / 400 for i in range(401)] + strikes
    vals = [(s, value_at(legs, s)) for s in sorted(set(grid))]
    pls = [v for _, v in vals]

    mx = max(pls)
    mn = min(pls)
    # detect unbounded tails (naked short / long single leaning to infinity)
    unbounded_up = any(lg.side == "buy" and lg.kind == "call" for lg in legs) and \
        not any(lg.side == "sell" and lg.kind == "call" for lg in legs)
    max_profit = None if (unbounded_up and value_at(legs, hi) >= mx) else round(mx, 2)

    naked_short = any(
        lg.side == "sell" and not any(o.side == "buy" and o.kind == lg.kind for o in legs)
        for lg in legs
    )
    max_loss = None if naked_short else round(mn, 2)

    # breakevens: sign changes across the grid
    bes = []
    for (s1, v1), (s2, v2) in zip(vals, vals[1:]):
        if (v1 <= 0 <= v2) or (v1 >= 0 >= v2):
            if v2 != v1:
                bes.append(round(s1 + (s2 - s1) * (-v1) / (v2 - v1), 2))
    # dedupe near-equal
    dedup = []
    for b in sorted(bes):
        if not dedup or abs(b - dedup[-1]) > 0.05:
            dedup.append(b)

    return Payoff(max_profit, max_loss, dedup, round(net, 2))

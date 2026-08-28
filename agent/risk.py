"""Deterministic risk gates. No model, no network. The manual desk surfaces
these as warnings; the (future) agent uses them as hard blocks."""
from __future__ import annotations
from dataclasses import dataclass
from agent import config


@dataclass
class Verdict:
    ok: bool
    warnings: list[str]


def check_order(*, contracts: int, contract_price: float, kind_is_defined_risk: bool,
                dte: int, equity: float, open_positions: int,
                daily_pl: float) -> Verdict:
    """contract_price = premium per share (max loss per contract = price*100 for
    a long; spreads pass their net debit). Returns warnings, never raises."""
    w: list[str] = []
    cost = contract_price * 100 * contracts

    if equity > 0 and cost > config.MAX_POSITION_PCT * equity:
        w.append(f"position ${cost:,.0f} > {config.MAX_POSITION_PCT:.0%} of equity "
                 f"(${config.MAX_POSITION_PCT*equity:,.0f})")
    if daily_pl < -config.MAX_DAILY_LOSS_PCT * equity:
        w.append(f"daily loss {daily_pl:,.0f} past halt "
                 f"(-{config.MAX_DAILY_LOSS_PCT:.0%} = -${config.MAX_DAILY_LOSS_PCT*equity:,.0f})")
    if open_positions >= config.MAX_OPEN_POSITIONS:
        w.append(f"{open_positions} open positions >= max {config.MAX_OPEN_POSITIONS}")
    if dte < config.MIN_DTE:
        w.append(f"{dte} DTE < min {config.MIN_DTE} (gamma risk)")
    if dte > config.MAX_DTE:
        w.append(f"{dte} DTE > max {config.MAX_DTE}")
    if not kind_is_defined_risk:
        w.append("undefined-risk (naked short) — not allowed by policy")

    return Verdict(ok=(len(w) == 0), warnings=w)

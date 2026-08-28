"""
Featherless AI sub-task: label the volatility regime for a ticker.

Responsibility split (see docs/DESIGN.md):
  - Claude  = the decision-maker (what to trade, how to size)
  - Featherless (this module) = a cheap, bounded CLASSIFIER call

It answers one narrow question — "given these IV stats, is this HIGH / NORMAL /
LOW implied vol?" — and returns a structured label. It never decides trades.
That keeps the expensive reasoning on Claude and offloads a mechanical
classification to a small open-source model, which is the honest reason to use
a second model at all.

Integrating Featherless is also what makes the project eligible for the
partner prize.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI
from agent.config import (
    FEATHERLESS_API_KEY,
    FEATHERLESS_BASE_URL,
    FEATHERLESS_MODEL,
)

Regime = Literal["HIGH", "NORMAL", "LOW", "UNKNOWN"]


@dataclass
class RegimeCall:
    ticker: str
    regime: Regime
    rationale: str
    source: str  # "featherless" or "fallback"


_SYSTEM = (
    "You are a volatility-regime classifier for an options trading agent. "
    "Given implied-volatility statistics for one US equity, respond with ONLY a "
    "JSON object: {\"regime\": \"HIGH\"|\"NORMAL\"|\"LOW\", \"rationale\": \"<=20 words\"}. "
    "HIGH means IV is rich relative to the ticker's own history (favor selling premium). "
    "LOW means IV is cheap (favor buying premium). No prose outside the JSON."
)


def _client() -> OpenAI | None:
    if not FEATHERLESS_API_KEY:
        return None
    return OpenAI(api_key=FEATHERLESS_API_KEY, base_url=FEATHERLESS_BASE_URL)


def classify_regime(ticker: str, iv_rank: float, iv: float, hv: float) -> RegimeCall:
    """
    iv_rank : 0-100 percentile of current IV vs the ticker's trailing IV range
    iv      : current implied vol (annualized, e.g. 0.85)
    hv      : realized/historical vol over the same window

    Deterministic fallback if Featherless is unavailable, so the agent NEVER
    blocks on a partner outage — the classifier is an enhancement, not a
    dependency.
    """
    client = _client()
    if client is None:
        return _fallback(ticker, iv_rank, iv, hv)

    user = (
        f"Ticker: {ticker}\n"
        f"IV rank (0-100): {iv_rank:.0f}\n"
        f"Implied vol: {iv:.2f}\n"
        f"Historical vol: {hv:.2f}\n"
        f"IV/HV ratio: {(iv / hv):.2f}" if hv else f"Ticker: {ticker}\nIV rank: {iv_rank:.0f}"
    )
    try:
        resp = client.chat.completions.create(
            model=FEATHERLESS_MODEL,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": user}],
            temperature=0,
            max_tokens=80,
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        regime = str(data.get("regime", "UNKNOWN")).upper()
        if regime not in ("HIGH", "NORMAL", "LOW"):
            regime = "UNKNOWN"
        return RegimeCall(ticker, regime, str(data.get("rationale", ""))[:120], "featherless")
    except Exception as e:  # bad JSON, timeout, rate limit -> deterministic path
        fb = _fallback(ticker, iv_rank, iv, hv)
        fb.rationale = f"featherless error ({type(e).__name__}); used fallback"
        return fb


def _fallback(ticker: str, iv_rank: float, iv: float, hv: float) -> RegimeCall:
    """Pure-rule regime label — the safety net."""
    if iv_rank >= 66:
        return RegimeCall(ticker, "HIGH", f"iv_rank {iv_rank:.0f} >= 66", "fallback")
    if iv_rank <= 33:
        return RegimeCall(ticker, "LOW", f"iv_rank {iv_rank:.0f} <= 33", "fallback")
    return RegimeCall(ticker, "NORMAL", f"iv_rank {iv_rank:.0f} mid-range", "fallback")


if __name__ == "__main__":
    # Smoke: works with or without a key (falls back cleanly).
    for tk, rank, iv, hv in [("MSTR", 82, 0.95, 0.60), ("COIN", 20, 0.45, 0.55)]:
        r = classify_regime(tk, rank, iv, hv)
        print(f"{r.ticker:5} {r.regime:7} [{r.source:11}] {r.rationale}")

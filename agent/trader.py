"""
Glaz momentum day-trade bot — ONE cycle. Paper only.

Strategy (per user directive): full-size directional options on the strongest
market trend. Buy calls into up-momentum, puts into down-momentum. Hard stop
loss, quick profit target. One position at a time. LIMIT orders only.

SAFETY: paper-only assert · kill-switch file (data/HALT) · daily-loss halt ·
equity floor circuit-breaker · every entry journaled.

Run one cycle:  uv run python -m agent.trader
Stop the bot:   touch data/HALT     (removes it to resume: rm data/HALT)
"""
from __future__ import annotations
import datetime as dt, json, math, os, sys
from pathlib import Path
from agent.config import require_alpaca, PAPER
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (GetOptionContractsRequest, LimitOrderRequest)
from alpaca.trading.enums import (ContractType, AssetStatus, OrderSide, OrderType, TimeInForce)
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockSnapshotRequest, OptionLatestQuoteRequest

# ---- parameters (aggressive, per directive) ----
UNIVERSE = ["MSTR","COIN","IBIT","MARA","RIOT","CRCL","HOOD","CLSK","CORZ","GLXY","BMNR"]
SIZE_PCT      = 0.90    # deploy 90% of buying power per trade ("full account")
STOP_PCT      = 0.25    # exit at -25% on the premium (stop loss)
TARGET_PCT    = 0.20    # exit at +20% (quick profit)
MOMENTUM_MIN  = 0.015   # need >=1.5% intraday trend to act (skip chop)
TARGET_DELTA  = 0.55    # slightly ITM for responsiveness
DTE_MIN, DTE_MAX = 7, 16
MAX_CONTRACTS = 1500
DAILY_HALT_PCT = 0.30   # stop new entries if down 30% on the day
EQUITY_FLOOR   = 40_000 # circuit-breaker: below this, no new entries
ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "data" / "journal.jsonl"
HALT = ROOT / "data" / "HALT"

def log(msg): print(f"[{_now()}] {msg}", flush=True)
def _now():
    from alpaca.trading.client import TradingClient  # timestamp from exchange clock
    return "cycle"
def journal(rec): 
    with open(JOURNAL, "a") as f: f.write(json.dumps(rec) + "\n")

def main():
    k, s = require_alpaca()
    if not PAPER:
        log("REFUSING: not a paper account."); sys.exit(2)
    tc = TradingClient(k, s, paper=True)
    od = OptionHistoricalDataClient(k, s); sd = StockHistoricalDataClient(k, s)

    if HALT.exists():
        log("HALT file present — bot paused. (rm data/HALT to resume)"); return

    clk = tc.get_clock()
    if not clk.is_open:
        log(f"market closed. next open {str(clk.next_open)[:19]}"); return

    acct = tc.get_account()
    equity = float(acct.equity); bp = float(acct.options_buying_power)
    daily_pl = float(acct.equity) - float(acct.last_equity)
    log(f"equity ${equity:,.0f} optbp ${bp:,.0f} dailyP&L ${daily_pl:,.0f}")

    positions = tc.get_all_positions()

    # ---- manage existing position: stop / target ----
    for p in positions:
        plpc = float(p.unrealized_plpc or 0)
        if plpc >= TARGET_PCT or plpc <= -STOP_PCT:
            reason = "target" if plpc >= TARGET_PCT else "stop"
            _close_limit(tc, od, p)
            log(f"EXIT {reason}: {p.symbol} at {plpc*100:+.1f}%")
            journal({"action":"exit","reason":reason,"symbol":p.symbol,
                     "pl_pct":round(plpc*100,1),"pl":float(p.unrealized_pl or 0)})
        else:
            log(f"hold {p.symbol} {plpc*100:+.1f}% (stop -{STOP_PCT*100:.0f} / tgt +{TARGET_PCT*100:.0f})")

    positions = tc.get_all_positions()
    if positions:
        log("position open — one at a time, no new entry this cycle."); return

    # ---- gates before a new entry ----
    if equity < EQUITY_FLOOR:
        log(f"equity below floor ${EQUITY_FLOOR:,} — circuit breaker, no entries."); return
    if daily_pl <= -DAILY_HALT_PCT * (equity - daily_pl):
        log("daily loss halt hit — no new entries today."); return

    # ---- momentum scan ----
    snaps = sd.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=UNIVERSE))
    best = None
    for sym in UNIVERSE:
        sn = snaps.get(sym)
        if not sn or not sn.latest_trade or not sn.daily_bar: continue
        last = float(sn.latest_trade.price); op = float(sn.daily_bar.open)
        pdb = getattr(sn, "previous_daily_bar", None)
        prev = float(pdb.close) if pdb else op
        intraday = (last - op) / op if op else 0
        overnight = (last - prev) / prev if prev else 0
        signal = 0.7 * intraday + 0.3 * overnight   # day-trade weights intraday
        if best is None or abs(signal) > abs(best[1]):
            best = (sym, signal, last)
    if not best or abs(best[1]) < MOMENTUM_MIN:
        log(f"no trend >= {MOMENTUM_MIN*100:.1f}% (best {best[0] if best else '-'} "
            f"{best[1]*100 if best else 0:+.2f}%) — no trade.")
        journal({"action":"no_trade","reason":"no trend","best":best[0] if best else None,
                 "signal_pct":round(best[1]*100,2) if best else None}); return

    sym, signal, spot = best
    ct = ContractType.CALL if signal > 0 else ContractType.PUT
    direction = "calls (uptrend)" if signal > 0 else "puts (downtrend)"
    log(f"TREND: {sym} {signal*100:+.2f}% -> {direction}")

    # ---- pick the option ----
    opt = _pick_option(tc, od, sym, ct, spot)
    if not opt:
        log(f"no liquid ~{TARGET_DELTA}delta option for {sym}"); return
    ask = opt["ask"]; contracts = min(MAX_CONTRACTS, int((SIZE_PCT * bp) // (ask * 100)))
    if contracts < 1:
        log("size < 1 contract — skip."); return

    # ---- enter with marketable LIMIT ----
    req = LimitOrderRequest(symbol=opt["symbol"], qty=contracts, side=OrderSide.BUY,
                            type=OrderType.LIMIT, time_in_force=TimeInForce.DAY,
                            limit_price=round(ask * 1.02, 2))  # marketable, +2% to fill
    o = tc.submit_order(req)
    cost = ask * 100 * contracts
    log(f"ENTER {contracts}x {opt['symbol']} @~${ask:.2f}  (~${cost:,.0f}, {contracts*ask*100/equity*100:.0f}% of equity) -> {str(o.status).split('.')[-1]}")
    journal({"action":"entry","underlying":sym,"structure":f"long {('call' if ct==ContractType.CALL else 'put')}",
             "symbol":opt["symbol"],"signal_pct":round(signal*100,2),"contracts":contracts,
             "entry_ask":ask,"cost":round(cost),"delta":opt["delta"],"dte":opt["dte"],
             "stop_pct":-STOP_PCT,"target_pct":TARGET_PCT,"order_id":str(o.id),
             "rationale":f"{direction} momentum {signal*100:+.2f}%, ~{TARGET_DELTA}delta, {opt['dte']}DTE, full size"})

def _pick_option(tc, od, sym, ct, spot):
    today = dt.date.today()
    req = GetOptionContractsRequest(underlying_symbols=[sym], status=AssetStatus.ACTIVE, type=ct,
        expiration_date_gte=today+dt.timedelta(days=DTE_MIN),
        expiration_date_lte=today+dt.timedelta(days=DTE_MAX), limit=300)
    cons = tc.get_option_contracts(req).option_contracts or []
    oi = {c.symbol:(int(c.open_interest) if c.open_interest else 0) for c in cons}
    try: chain = od.get_option_chain(OptionChainRequest(underlying_symbol=sym, type=ct))
    except: chain = {}
    best = None
    for osym, c in {c.symbol:c for c in cons}.items():
        sn = chain.get(osym)
        if not sn: continue
        g = getattr(sn,"greeks",None); q = getattr(sn,"latest_quote",None)
        if not g or g.delta is None or not q or not q.ask_price or not q.bid_price: continue
        if oi.get(osym,0) < 100: continue
        spr = (float(q.ask_price)-float(q.bid_price))/((float(q.ask_price)+float(q.bid_price))/2)
        if spr > 0.15: continue
        d = abs(float(g.delta))
        if best is None or abs(d-TARGET_DELTA) < abs(best["delta_diff"]):
            best = {"symbol":osym,"ask":float(q.ask_price),"bid":float(q.bid_price),
                    "delta":round(float(g.delta),3),"delta_diff":d-TARGET_DELTA,
                    "dte":(dt.date.fromisoformat(str(c.expiration_date))-today).days}
    return best

def _close_limit(tc, od, p):
    q = od.get_option_latest_quote(OptionLatestQuoteRequest(symbol_or_symbols=[p.symbol])).get(p.symbol)
    bid = float(q.bid_price) if q and q.bid_price else 0.01
    from alpaca.trading.requests import LimitOrderRequest
    tc.submit_order(LimitOrderRequest(symbol=p.symbol, qty=abs(int(float(p.qty))),
        side=OrderSide.SELL, type=OrderType.LIMIT, time_in_force=TimeInForce.DAY,
        limit_price=round(bid*0.98, 2)))  # marketable sell

if __name__ == "__main__":
    main()

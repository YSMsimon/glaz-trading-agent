"""
Glaz Manual Desk — monitor + trade. Options terminal on Alpaca (paper), localhost.
No agent. Keys stay server-side. Run: uv run python -m frontend.server
"""
from __future__ import annotations
import datetime as dt, re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOptionContractsRequest, MarketOrderRequest, LimitOrderRequest,
    StopOrderRequest, StopLimitOrderRequest, GetOrdersRequest, OptionLegRequest,
    GetPortfolioHistoryRequest,
)
from alpaca.trading.enums import (
    OrderSide, OrderType, TimeInForce, ContractType, AssetStatus,
    QueryOrderStatus, OrderClass,
)
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockSnapshotRequest
from agent.config import require_alpaca, PAPER
from agent import risk

app = FastAPI(title="Glaz Manual Desk")

def _k(): return require_alpaca()
def trading(): k, s = _k(); return TradingClient(k, s, paper=PAPER)
def opt_data(): k, s = _k(); return OptionHistoricalDataClient(k, s)
def stock_data(): k, s = _k(); return StockHistoricalDataClient(k, s)

# OCC symbol decode: MSTR260918C00133000 -> MSTR 2026-09-18 C 133
_OCC = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
def decode(sym: str) -> str:
    m = _OCC.match(sym)
    if not m: return sym
    u, y, mo, d, cp, strike = m.groups()
    return f"{u} {int(strike)/1000:g}{cp} {y}-{mo}-{d}"

# ---------------- monitor: account / positions / orders / activities ----------------

@app.get("/api/account")
def account():
    a = trading().get_account()
    return {"id": str(a.id), "number": getattr(a, "account_number", None),
            "equity": float(a.equity), "cash": float(a.cash),
            "buying_power": float(a.buying_power),
            "options_bp": float(getattr(a, "options_buying_power", 0) or 0),
            "options_level": getattr(a, "options_trading_level", None),
            "daily_pl": float(a.equity) - float(a.last_equity),
            "last_equity": float(a.last_equity)}

@app.get("/api/positions")
def positions():
    out = []
    for p in trading().get_all_positions():
        is_opt = bool(_OCC.match(p.symbol))
        out.append({
            "symbol": p.symbol, "label": decode(p.symbol) if is_opt else p.symbol,
            "is_option": is_opt, "qty": float(p.qty), "side": str(p.side).split(".")[-1].lower(),
            "avg_price": float(p.avg_entry_price),
            "current": float(p.current_price or 0),
            "cost_basis": float(p.cost_basis or 0),
            "market_value": float(p.market_value or 0),
            "unrealized_pl": float(p.unrealized_pl or 0),
            "unrealized_plpc": float(p.unrealized_plpc or 0) * 100})
    return out

@app.post("/api/positions/close")
def close_position(body: dict):
    sym = body.get("symbol")
    if not sym: raise HTTPException(400, "symbol required")
    try:
        r = trading().close_position(sym)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@app.post("/api/positions/close_all")
def close_all():
    try:
        trading().close_all_positions(cancel_orders=True)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@app.get("/api/orders")
def orders(status: str = "open"):
    qs = {"open": QueryOrderStatus.OPEN, "closed": QueryOrderStatus.CLOSED}.get(status, QueryOrderStatus.ALL)
    req = GetOrdersRequest(status=qs, limit=100, nested=True)
    out = []
    for o in trading().get_orders(req):
        is_opt = bool(_OCC.match(o.symbol or ""))
        out.append({"id": str(o.id), "symbol": o.symbol,
                    "label": decode(o.symbol) if is_opt else o.symbol,
                    "side": str(o.side).split(".")[-1], "qty": float(o.qty or 0),
                    "type": str(o.order_type).split(".")[-1], "tif": str(o.time_in_force).split(".")[-1],
                    "limit": float(o.limit_price) if o.limit_price else None,
                    "stop": float(o.stop_price) if o.stop_price else None,
                    "status": str(o.status).split(".")[-1],
                    "filled_qty": float(o.filled_qty or 0),
                    "filled_avg": float(o.filled_avg_price) if o.filled_avg_price else None,
                    "submitted": str(o.submitted_at)[:19] if o.submitted_at else None,
                    "cancellable": str(o.status).split(".")[-1] in ("NEW","PENDING_NEW","ACCEPTED","PARTIALLY_FILLED","HELD")})
    return out

@app.post("/api/orders/{order_id}/cancel")
def cancel(order_id: str):
    try:
        trading().cancel_order_by_id(order_id); return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@app.get("/api/activities")
def activities():
    """Recent fills, derived from closed orders (account-activities API not in this SDK)."""
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=60, nested=True)
        orders = trading().get_orders(req)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    out = []
    for o in orders:
        if not o.filled_qty or float(o.filled_qty) == 0:
            continue
        sym = o.symbol or ""
        out.append({"type": str(o.status).split(".")[-1],
                    "symbol": sym, "label": decode(sym) if _OCC.match(sym) else sym,
                    "side": str(o.side).split(".")[-1],
                    "qty": float(o.filled_qty),
                    "price": float(o.filled_avg_price) if o.filled_avg_price else None,
                    "value": (float(o.filled_avg_price) * float(o.filled_qty) * (100 if _OCC.match(sym) else 1)) if o.filled_avg_price else None,
                    "date": str(o.filled_at or o.submitted_at or "")[:19]})
    return out


# ---------------- watchlist: crypto-related equities & ETFs ----------------

CRYPTO_UNIVERSE = {
    "Proxy / Treasury": ["MSTR", "BMNR", "SBET"],
    "Exchanges / Brokers": ["COIN", "HOOD", "GLXY", "CRCL"],
    "Miners / Data-center": ["MARA", "RIOT", "CLSK", "CIFR", "WULF", "IREN",
                              "CORZ", "HUT", "BITF", "BTDR", "APLD", "HIVE"],
    "ETFs": ["IBIT", "FBTC", "BITO", "GBTC", "BITX"],
}
_ALL_SYMS = [s for g in CRYPTO_UNIVERSE.values() for s in g]

@app.get("/api/universe")
def universe():
    return CRYPTO_UNIVERSE

@app.get("/api/watchlist")
def watchlist(symbols: str = ""):
    syms = [x.strip().upper() for x in symbols.split(",") if x.strip()] or _ALL_SYMS
    try:
        snaps = stock_data().get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=syms))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    out = []
    for sym in syms:
        s = snaps.get(sym)
        if not s:
            out.append({"symbol": sym, "price": None, "change": None, "changepct": None}); continue
        lt = getattr(s, "latest_trade", None)
        db = getattr(s, "daily_bar", None)
        pdb = getattr(s, "previous_daily_bar", None)
        price = float(lt.price) if lt and lt.price else (float(db.close) if db else None)
        prev = float(pdb.close) if pdb and pdb.close else None
        chg = (price - prev) if (price is not None and prev) else None
        pct = (chg / prev * 100) if (chg is not None and prev) else None
        out.append({"symbol": sym, "price": round(price, 2) if price else None,
                    "change": round(chg, 2) if chg is not None else None,
                    "changepct": round(pct, 2) if pct is not None else None})
    return out

# ---------------- option information: chain search ----------------

@app.get("/api/chain")
def chain(symbol: str, kind: str = "call", dte_min: int = 7, dte_max: int = 45):
    sym = symbol.upper()
    ct = ContractType.CALL if kind.lower().startswith("c") else ContractType.PUT
    today = dt.date.today()
    req = GetOptionContractsRequest(underlying_symbols=[sym], status=AssetStatus.ACTIVE, type=ct,
        expiration_date_gte=today + dt.timedelta(days=dte_min),
        expiration_date_lte=today + dt.timedelta(days=dte_max), limit=300)
    contracts = trading().get_option_contracts(req).option_contracts or []
    meta = {c.symbol: {"strike": float(c.strike_price), "expiry": str(c.expiration_date),
                       "oi": int(c.open_interest) if c.open_interest else None} for c in contracts}
    try:
        snaps = opt_data().get_option_chain(OptionChainRequest(underlying_symbol=sym, type=ct)) or {}
    except Exception:
        snaps = {}
    rows = []
    for osym, m in meta.items():
        s = snaps.get(osym); q = getattr(s, "latest_quote", None) if s else None
        g = getattr(s, "greeks", None) if s else None
        rows.append({"symbol": osym, "strike": m["strike"], "expiry": m["expiry"], "oi": m["oi"],
            "bid": float(q.bid_price) if q and q.bid_price else None,
            "ask": float(q.ask_price) if q and q.ask_price else None,
            "iv": round(float(s.implied_volatility), 3) if s and s.implied_volatility else None,
            "delta": round(float(g.delta), 3) if g and g.delta is not None else None,
            "theta": round(float(g.theta), 3) if g and g.theta is not None else None,
            "gamma": round(float(g.gamma), 4) if g and g.gamma is not None else None,
            "vega": round(float(g.vega), 3) if g and g.vega is not None else None,
            "dte": (dt.date.fromisoformat(m["expiry"]) - today).days})
    rows.sort(key=lambda r: (r["expiry"], r["strike"]))
    return rows

# ---------------- trade: single-leg (advanced) ----------------

class Order(BaseModel):
    symbol: str; side: str = "buy"; qty: int = 1
    type: str = "market"                      # market|limit|stop|stop_limit
    limit_price: float | None = None
    stop_price: float | None = None
    tif: str = "day"                          # day|gtc

@app.post("/api/order")
def place(o: Order):
    side = OrderSide.BUY if o.side == "buy" else OrderSide.SELL
    tif = TimeInForce.GTC if o.tif == "gtc" else TimeInForce.DAY
    try:
        common = dict(symbol=o.symbol, qty=o.qty, side=side, time_in_force=tif)
        if o.type == "market":
            req = MarketOrderRequest(type=OrderType.MARKET, **common)
        elif o.type == "limit":
            if not o.limit_price: raise HTTPException(400, "limit_price required")
            req = LimitOrderRequest(type=OrderType.LIMIT, limit_price=o.limit_price, **common)
        elif o.type == "stop":
            if not o.stop_price: raise HTTPException(400, "stop_price required")
            req = StopOrderRequest(type=OrderType.STOP, stop_price=o.stop_price, **common)
        elif o.type == "stop_limit":
            if not (o.stop_price and o.limit_price): raise HTTPException(400, "stop_price and limit_price required")
            req = StopLimitOrderRequest(type=OrderType.STOP_LIMIT, stop_price=o.stop_price,
                                        limit_price=o.limit_price, **common)
        else:
            raise HTTPException(400, f"unknown type {o.type}")
        r = trading().submit_order(req)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status).split(".")[-1],
                "symbol": r.symbol, "qty": float(r.qty or 0), "side": o.side}
    except HTTPException: raise
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

# ---------------- trade: multi-leg + preview ----------------

class LegIn(BaseModel):
    side: str; kind: str; strike: float; price: float; qty: int = 1; symbol: str | None = None

class PreviewIn(BaseModel):
    legs: list[LegIn]; dte: int = 21

@app.post("/api/preview")
def preview(p: PreviewIn):
    from agent.analytics import Leg, analyze
    legs = [Leg(l.side, l.kind, l.strike, l.price, l.qty) for l in p.legs]
    pay = analyze(legs); defined = pay.max_loss is not None
    try:
        acct = trading().get_account(); equity = float(acct.equity)
        dpl = float(acct.equity) - float(acct.last_equity); nopen = len(trading().get_all_positions())
    except Exception:
        equity, dpl, nopen = 100_000.0, 0.0, 0
    worst = abs(pay.max_loss) / 100 if pay.max_loss else max(l.price for l in p.legs)
    v = risk.check_order(contracts=max(l.qty for l in p.legs), contract_price=worst,
        kind_is_defined_risk=defined, dte=p.dte, equity=equity, open_positions=nopen, daily_pl=dpl)
    return {"max_profit": pay.max_profit, "max_loss": pay.max_loss, "breakevens": pay.breakevens,
            "net": pay.net, "risk_ok": v.ok, "warnings": v.warnings}

class MultiLeg(BaseModel):
    legs: list[LegIn]; qty: int = 1; type: str = "market"; limit_price: float | None = None

@app.post("/api/order/multileg")
def place_multileg(m: MultiLeg):
    try:
        if any(not l.symbol for l in m.legs): raise HTTPException(400, "each leg needs its OCC symbol")
        legs = [OptionLegRequest(symbol=l.symbol, ratio_qty=l.qty,
                    side=OrderSide.BUY if l.side == "buy" else OrderSide.SELL) for l in m.legs]
        common = dict(qty=m.qty, order_class=OrderClass.MLEG, time_in_force=TimeInForce.DAY, legs=legs)
        if m.type == "limit":
            if m.limit_price is None: raise HTTPException(400, "limit_price required")
            req = LimitOrderRequest(type=OrderType.LIMIT, limit_price=m.limit_price, **common)
        else:
            req = MarketOrderRequest(type=OrderType.MARKET, **common)
        r = trading().submit_order(req)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status).split(".")[-1]}
    except HTTPException: raise
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

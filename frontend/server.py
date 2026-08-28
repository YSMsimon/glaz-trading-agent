"""
Glaz Manual Desk — human-driven options trading on Alpaca (paper), localhost.
No agent. Keys stay server-side. Run: uv run python -m frontend.server
"""
from __future__ import annotations
import datetime as dt
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOptionContractsRequest, MarketOrderRequest, LimitOrderRequest,
    GetOrdersRequest, OptionLegRequest,
)
from alpaca.trading.enums import (
    OrderSide, OrderType, TimeInForce, ContractType, AssetStatus,
    QueryOrderStatus, OrderClass, PositionIntent,
)
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from agent.config import require_alpaca, PAPER
from agent import risk

app = FastAPI(title="Glaz Manual Desk")

def _keys():
    return require_alpaca()

def trading() -> TradingClient:
    k, s = _keys(); return TradingClient(k, s, paper=PAPER)

def opt_data() -> OptionHistoricalDataClient:
    k, s = _keys(); return OptionHistoricalDataClient(k, s)

def stock_data() -> StockHistoricalDataClient:
    k, s = _keys(); return StockHistoricalDataClient(k, s)

# ---------------- account / tracker ----------------

@app.get("/api/account")
def account():
    a = trading().get_account()
    return {"id": str(a.id), "equity": float(a.equity), "cash": float(a.cash),
            "buying_power": float(a.buying_power),
            "options_bp": float(getattr(a, "options_buying_power", 0) or 0),
            "options_level": getattr(a, "options_trading_level", None),
            "daily_pl": float(a.equity) - float(a.last_equity)}

@app.get("/api/positions")
def positions():
    out = []
    for p in trading().get_all_positions():
        out.append({"symbol": p.symbol, "qty": float(p.qty),
                    "avg_price": float(p.avg_entry_price),
                    "market_value": float(p.market_value or 0),
                    "unrealized_pl": float(p.unrealized_pl or 0),
                    "asset_class": str(p.asset_class)})
    return out

@app.get("/api/orders")
def orders(status: str = "open"):
    qs = QueryOrderStatus.OPEN if status == "open" else QueryOrderStatus.ALL
    req = GetOrdersRequest(status=qs, limit=50, nested=True)
    out = []
    for o in trading().get_orders(req):
        out.append({"id": str(o.id), "symbol": o.symbol, "side": str(o.side),
                    "qty": float(o.qty or 0), "type": str(o.order_type),
                    "status": str(o.status),
                    "filled_avg": float(o.filled_avg_price) if o.filled_avg_price else None,
                    "submitted": str(o.submitted_at)[:19] if o.submitted_at else None})
    return out

@app.post("/api/orders/{order_id}/cancel")
def cancel(order_id: str):
    try:
        trading().cancel_order_by_id(order_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

# ---------------- options search (join OI + greeks/IV) ----------------

@app.get("/api/chain")
def chain(symbol: str, kind: str = "call", dte_min: int = 7, dte_max: int = 45):
    sym = symbol.upper()
    ct = ContractType.CALL if kind.lower().startswith("c") else ContractType.PUT
    today = dt.date.today()

    # 1) contracts -> strike, expiry, open interest
    req = GetOptionContractsRequest(
        underlying_symbols=[sym], status=AssetStatus.ACTIVE, type=ct,
        expiration_date_gte=today + dt.timedelta(days=dte_min),
        expiration_date_lte=today + dt.timedelta(days=dte_max), limit=200)
    contracts = trading().get_option_contracts(req).option_contracts or []
    meta = {c.symbol: {"strike": float(c.strike_price), "expiry": str(c.expiration_date),
                       "oi": int(c.open_interest) if c.open_interest else None}
            for c in contracts}

    # 2) live snapshot -> quote + greeks + IV (best-effort; may be empty off-hours)
    snaps = {}
    try:
        cr = OptionChainRequest(underlying_symbol=sym, type=ct)
        snaps = opt_data().get_option_chain(cr) or {}
    except Exception:
        snaps = {}

    rows = []
    for osym, m in meta.items():
        s = snaps.get(osym)
        q = getattr(s, "latest_quote", None) if s else None
        g = getattr(s, "greeks", None) if s else None
        rows.append({
            "symbol": osym, "strike": m["strike"], "expiry": m["expiry"], "oi": m["oi"],
            "bid": float(q.bid_price) if q and q.bid_price else None,
            "ask": float(q.ask_price) if q and q.ask_price else None,
            "iv": round(float(s.implied_volatility), 3) if s and s.implied_volatility else None,
            "delta": round(float(g.delta), 3) if g and g.delta is not None else None,
            "theta": round(float(g.theta), 3) if g and g.theta is not None else None,
            "gamma": round(float(g.gamma), 4) if g and g.gamma is not None else None,
            "vega": round(float(g.vega), 3) if g and g.vega is not None else None,
            "dte": (dt.date.fromisoformat(m["expiry"]) - today).days,
        })
    rows.sort(key=lambda r: (r["expiry"], r["strike"]))
    return rows

@app.get("/api/bars")
def bars(symbol: str, days: int = 60):
    """Underlying daily closes for the price chart."""
    end = dt.date.today()
    req = StockBarsRequest(symbol_or_symbols=[symbol.upper()], timeframe=TimeFrame.Day,
                           start=end - dt.timedelta(days=days), end=end)
    try:
        bs = stock_data().get_stock_bars(req)
        data = bs.data.get(symbol.upper(), [])
        return [{"t": str(b.timestamp)[:10], "c": float(b.close)} for b in data]
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

# ---------------- preview + risk ----------------

class LegIn(BaseModel):
    side: str; kind: str; strike: float; price: float; qty: int = 1
    symbol: str | None = None  # OCC symbol (required for multileg submit)

class PreviewIn(BaseModel):
    legs: list[LegIn]
    dte: int = 21

@app.post("/api/preview")
def preview(p: PreviewIn):
    from agent.analytics import Leg, analyze
    legs = [Leg(l.side, l.kind, l.strike, l.price, l.qty) for l in p.legs]
    pay = analyze(legs)
    defined = pay.max_loss is not None
    try:
        acct = trading().get_account()
        equity = float(acct.equity); dpl = float(acct.equity) - float(acct.last_equity)
        nopen = len(trading().get_all_positions())
    except Exception:
        equity, dpl, nopen = 100_000.0, 0.0, 0
    worst = abs(pay.max_loss) / 100 if pay.max_loss else max(l.price for l in p.legs)
    v = risk.check_order(contracts=max(l.qty for l in p.legs), contract_price=worst,
                         kind_is_defined_risk=defined, dte=p.dte, equity=equity,
                         open_positions=nopen, daily_pl=dpl)
    return {"max_profit": pay.max_profit, "max_loss": pay.max_loss,
            "breakevens": pay.breakevens, "net": pay.net,
            "risk_ok": v.ok, "warnings": v.warnings}

# ---------------- order submission ----------------

class Order(BaseModel):
    symbol: str; side: str = "buy"; qty: int = 1
    type: str = "market"; limit_price: float | None = None

@app.post("/api/order")
def place(o: Order):
    side = OrderSide.BUY if o.side == "buy" else OrderSide.SELL
    try:
        if o.type == "limit":
            if not o.limit_price:
                raise HTTPException(400, "limit_price required")
            req = LimitOrderRequest(symbol=o.symbol, qty=o.qty, side=side,
                                    type=OrderType.LIMIT, time_in_force=TimeInForce.DAY,
                                    limit_price=o.limit_price)
        else:
            req = MarketOrderRequest(symbol=o.symbol, qty=o.qty, side=side,
                                     type=OrderType.MARKET, time_in_force=TimeInForce.DAY)
        r = trading().submit_order(req)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status),
                "symbol": r.symbol, "qty": float(r.qty or 0), "side": str(r.side)}
    except HTTPException: raise
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

class MultiLeg(BaseModel):
    legs: list[LegIn]
    qty: int = 1
    type: str = "market"
    limit_price: float | None = None

@app.post("/api/order/multileg")
def place_multileg(m: MultiLeg):
    """Submit a spread / multi-leg as ONE order. Each leg needs its OCC symbol."""
    try:
        if any(not l.symbol for l in m.legs):
            raise HTTPException(400, "each leg needs its OCC symbol")
        legs = [OptionLegRequest(
                    symbol=l.symbol, ratio_qty=l.qty,
                    side=OrderSide.BUY if l.side == "buy" else OrderSide.SELL)
                for l in m.legs]
        common = dict(qty=m.qty, order_class=OrderClass.MLEG,
                      time_in_force=TimeInForce.DAY, legs=legs)
        if m.type == "limit":
            if m.limit_price is None:
                raise HTTPException(400, "limit_price required")
            req = LimitOrderRequest(type=OrderType.LIMIT, limit_price=m.limit_price, **common)
        else:
            req = MarketOrderRequest(type=OrderType.MARKET, **common)
        r = trading().submit_order(req)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status),
                "legs": [l.symbol for l in m.legs]}
    except HTTPException: raise
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

# ---------------- page ----------------

@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

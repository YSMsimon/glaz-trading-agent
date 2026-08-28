"""
Manual options-trading dashboard — localhost only.

A human clicks trades; NO agent, NO autonomy. Keys stay server-side (never
sent to the browser). This is the "try it by hand first" surface, separate
from the autonomous agent.

Run:  uv run python -m frontend.server   ->  http://127.0.0.1:8000
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
)
from alpaca.trading.enums import (
    OrderSide, OrderType, TimeInForce, ContractType, AssetStatus,
)
from agent.config import require_alpaca, PAPER

app = FastAPI(title="Glaz Manual Desk")

def client() -> TradingClient:
    api_key, secret = require_alpaca()
    return TradingClient(api_key, secret, paper=PAPER)

# ---------- read endpoints ----------

@app.get("/api/account")
def account():
    a = client().get_account()
    return {
        "id": str(a.id),
        "equity": float(a.equity),
        "cash": float(a.cash),
        "buying_power": float(a.buying_power),
        "options_bp": float(getattr(a, "options_buying_power", 0) or 0),
        "options_level": getattr(a, "options_trading_level", None),
        "daily_pl": float(a.equity) - float(a.last_equity),
    }

@app.get("/api/positions")
def positions():
    out = []
    for p in client().get_all_positions():
        out.append({
            "symbol": p.symbol, "qty": float(p.qty),
            "avg_price": float(p.avg_entry_price),
            "market_value": float(p.market_value or 0),
            "unrealized_pl": float(p.unrealized_pl or 0),
            "asset_class": str(p.asset_class),
        })
    return out

@app.get("/api/chain")
def chain(symbol: str, kind: str = "call", limit: int = 40):
    """Option contracts for an underlying, nearest expiries first."""
    ct = ContractType.CALL if kind.lower().startswith("c") else ContractType.PUT
    today = dt.date.today()
    req = GetOptionContractsRequest(
        underlying_symbols=[symbol.upper()],
        status=AssetStatus.ACTIVE,
        type=ct,
        expiration_date_gte=today + dt.timedelta(days=7),
        expiration_date_lte=today + dt.timedelta(days=45),
        limit=limit,
    )
    res = client().get_option_contracts(req)
    rows = []
    for c in res.option_contracts or []:
        rows.append({
            "symbol": c.symbol, "strike": float(c.strike_price),
            "expiry": str(c.expiration_date), "type": str(c.type),
            "oi": int(c.open_interest or 0) if c.open_interest else None,
            "close": float(c.close_price) if c.close_price else None,
        })
    rows.sort(key=lambda r: (r["expiry"], r["strike"]))
    return rows

# ---------- order endpoint ----------

class Order(BaseModel):
    symbol: str            # OCC option symbol from the chain
    side: str = "buy"      # buy | sell
    qty: int = 1
    type: str = "market"   # market | limit
    limit_price: float | None = None

@app.post("/api/order")
def place(o: Order):
    side = OrderSide.BUY if o.side == "buy" else OrderSide.SELL
    tif = TimeInForce.DAY
    try:
        if o.type == "limit":
            if not o.limit_price:
                raise HTTPException(400, "limit_price required for a limit order")
            req = LimitOrderRequest(symbol=o.symbol, qty=o.qty, side=side,
                                    type=OrderType.LIMIT, time_in_force=tif,
                                    limit_price=o.limit_price)
        else:
            req = MarketOrderRequest(symbol=o.symbol, qty=o.qty, side=side,
                                     type=OrderType.MARKET, time_in_force=tif)
        r = client().submit_order(req)
        return {"ok": True, "order_id": str(r.id), "status": str(r.status),
                "symbol": r.symbol, "qty": float(r.qty or 0), "side": str(r.side)}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

# ---------- static page ----------

@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

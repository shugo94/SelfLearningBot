"""HTTP routes — all UI calls land here."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import datetime

from ..backtest.engine import run as run_backtest
from ..config import settings
from ..data import get_data_source, reload as reload_data_source
from ..data.angel_one import AngelOneDataSource
from ..db.models import BrokerCredentials, LearningLog, Trade
from ..db.session import get_session
from ..ml.rl_tuner import load_params
from ..ml.xgb_model import XGBSignal
from ..screener.ranker import rank
from ..strategy.ma_crossover import MACrossoverStrategy
from ..trading.paper_broker import OrderResult, place_order, portfolio_value

router = APIRouter(prefix="/api")


# ----- market data -----

@router.get("/quote")
def quote(symbol: str) -> dict:
    q = get_data_source().quote(symbol)
    return q.__dict__


@router.get("/history")
def history(symbol: str, period: str = "6mo", interval: str = "1d") -> dict:
    df = get_data_source().history(symbol, period, interval)
    if df.empty:
        raise HTTPException(404, f"no history for {symbol}")
    return {
        "symbol": symbol,
        "candles": [
            {
                "time": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                "open": float(row["Open"]), "high": float(row["High"]),
                "low": float(row["Low"]), "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for idx, row in df.iterrows()
        ],
    }


# ----- AI signal -----

@router.get("/signal")
def signal(symbol: str) -> dict:
    src = get_data_source()
    df = src.history(symbol, period="6mo", interval="1d")
    if df.empty:
        raise HTTPException(404, "no history")
    with get_session() as s:
        params = load_params(s, "ma_crossover")
    strat = MACrossoverStrategy(params=params)
    sig = strat.signal(df)

    ml = XGBSignal()
    p_up = ml.predict_proba(df)

    blended_conf = sig.confidence
    if p_up is not None and sig.action == "BUY":
        blended_conf = float(0.6 * sig.confidence + 0.4 * p_up)

    return {
        "symbol": symbol,
        "action": sig.action,
        "rule_confidence": round(sig.confidence, 3),
        "ml_p_up": round(p_up, 3) if p_up is not None else None,
        "blended_confidence": round(blended_conf, 3),
        "reason": sig.reason,
        "stop_loss": sig.stop_loss,
        "target": sig.target,
        "params": params.__dict__,
    }


class TrainBody(BaseModel):
    symbol: str
    period: str = "5y"


@router.post("/ml/train")
def train_ml(body: TrainBody) -> dict:
    src = get_data_source()
    df = src.history(body.symbol, period=body.period, interval="1d")
    if df.empty:
        raise HTTPException(404, "no history to train on")
    return XGBSignal().fit(df)


# ----- screener -----

@router.get("/screener")
def screener(top_n: int = 10) -> list[dict]:
    return rank(top_n=top_n)


# ----- backtest -----

class BacktestBody(BaseModel):
    symbol: str
    period: str = "2y"
    interval: str = "1d"


@router.post("/backtest")
def backtest(body: BacktestBody) -> dict:
    df = get_data_source().history(body.symbol, period=body.period, interval=body.interval)
    if df.empty:
        raise HTTPException(404, "no history")
    with get_session() as s:
        params = load_params(s, "ma_crossover")
    res = run_backtest(df, strategy=MACrossoverStrategy(params=params))
    return {
        "symbol": body.symbol, "period": body.period,
        "metrics": res.metrics,
        "equity_curve": res.equity_curve[-200:],  # cap payload
        "trades": res.trades,
    }


# ----- trading -----

class OrderBody(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: int
    strategy: str = "manual"
    confidence: float = 0.0
    reason: str = ""


@router.post("/order")
def order(body: OrderBody) -> dict:
    r: OrderResult = place_order(
        body.symbol, body.side, body.qty,
        strategy=body.strategy, confidence=body.confidence, reason=body.reason,
    )
    if not r.ok:
        raise HTTPException(400, r.message)
    return r.__dict__


@router.get("/portfolio")
def portfolio() -> dict:
    return portfolio_value()


@router.get("/trades")
def trades(limit: int = 50) -> list[dict]:
    with get_session() as s:
        rows = s.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": t.id, "symbol": t.symbol, "side": t.side, "qty": t.qty,
                "price": t.price, "timestamp": t.timestamp.isoformat(),
                "strategy": t.strategy, "confidence": t.confidence,
                "reason": t.reason, "pnl": t.pnl,
            }
            for t in rows
        ]


# ----- learning log -----

@router.get("/learning")
def learning(limit: int = 50) -> list[dict]:
    with get_session() as s:
        rows = s.query(LearningLog).order_by(LearningLog.timestamp.desc()).limit(limit).all()
        return [
            {"id": r.id, "timestamp": r.timestamp.isoformat(), "kind": r.kind, "message": r.message}
            for r in rows
        ]


@router.get("/config")
def config() -> dict:
    return {
        "data_source": settings.data_source,
        "starting_cash": settings.starting_cash,
        "default_universe": list(settings.default_universe),
    }


# ----- broker credentials -----

class BrokerCredsBody(BaseModel):
    api_key: str
    client_id: str
    password: str
    totp_secret: str


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "•" * len(value)
    return f"{value[:2]}{'•' * (len(value) - 4)}{value[-2:]}"


@router.get("/broker/status")
def broker_status() -> dict:
    """Return current broker config WITHOUT exposing secrets."""
    with get_session() as s:
        row = s.get(BrokerCredentials, "angel_one")
        if row is None:
            return {
                "configured": False,
                "active_source": "yahoo",
                "broker": None,
                "last_login_at": None,
                "last_error": None,
            }
        return {
            "configured": True,
            "active_source": "angel_one",
            "broker": "angel_one",
            "api_key_preview": _mask(row.api_key),
            "client_id": row.client_id,  # not really secret
            "totp_secret_preview": _mask(row.totp_secret),
            "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
            "last_error": row.last_error,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


@router.post("/broker/credentials")
def save_broker_credentials(body: BrokerCredsBody) -> dict:
    """Upsert Angel One credentials and reset the data-source cache."""
    if not all([body.api_key, body.client_id, body.password, body.totp_secret]):
        raise HTTPException(400, "all four fields are required")
    with get_session() as s:
        row = s.get(BrokerCredentials, "angel_one")
        if row is None:
            row = BrokerCredentials(broker="angel_one")
            s.add(row)
        row.api_key = body.api_key.strip()
        row.client_id = body.client_id.strip()
        row.password = body.password
        # Strip whitespace from TOTP secret — common copy-paste foot-gun.
        row.totp_secret = body.totp_secret.replace(" ", "").strip()
        row.last_error = None
    reload_data_source()
    return broker_status()


@router.delete("/broker/credentials")
def delete_broker_credentials() -> dict:
    with get_session() as s:
        row = s.get(BrokerCredentials, "angel_one")
        if row is not None:
            s.delete(row)
    reload_data_source()
    return broker_status()


@router.post("/broker/test")
def test_broker_connection() -> dict:
    """Force a login + lightweight quote round-trip. Persist outcome."""
    src = get_data_source()
    if not isinstance(src, AngelOneDataSource):
        raise HTTPException(400, "Angel One credentials not configured")
    try:
        session = src.login()
        # Try a real quote so we exercise instrument resolution + LTP.
        sample = src.quote("RELIANCE.NS")
        with get_session() as s:
            row = s.get(BrokerCredentials, "angel_one")
            if row:
                row.last_login_at = datetime.utcnow()
                row.last_error = None
        return {
            "ok": True,
            "message": "Logged in and fetched a live quote.",
            "sample_quote": sample.__dict__,
            "session_status": bool(session.get("status")),
        }
    except Exception as e:
        with get_session() as s:
            row = s.get(BrokerCredentials, "angel_one")
            if row:
                row.last_error = str(e)[:500]
        raise HTTPException(400, f"connection failed: {e}")

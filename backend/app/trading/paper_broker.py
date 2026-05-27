"""Paper broker — executes against the current live price from the DataSource.

Single-account, long-only, integer-share for v1. P&L is realized on close
and routed back to the RL tuner so the system learns.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..data import get_data_source
from ..db.models import CashAccount, LearningLog, Position, Trade
from ..db.session import get_session
from ..ml.rl_tuner import record_reward


@dataclass
class OrderResult:
    ok: bool
    message: str
    trade_id: int | None = None
    fill_price: float | None = None
    realized_pnl: float = 0.0


def _cash_row(s: Session) -> CashAccount:
    row = s.query(CashAccount).first()
    if row is None:
        row = CashAccount(cash=0.0)
        s.add(row)
        s.flush()
    return row


def place_order(
    symbol: str, side: str, qty: int, *,
    strategy: str = "manual", confidence: float = 0.0, reason: str = "",
) -> OrderResult:
    side = side.upper()
    if side not in {"BUY", "SELL"} or qty <= 0:
        return OrderResult(False, "invalid order")

    quote = get_data_source().quote(symbol)
    price = quote.price

    with get_session() as s:
        cash = _cash_row(s)
        pos = s.get(Position, symbol)
        realized = 0.0

        if side == "BUY":
            cost = price * qty
            if cash.cash < cost:
                return OrderResult(False, f"insufficient cash: need {cost:.2f}, have {cash.cash:.2f}")
            cash.cash -= cost
            if pos is None:
                pos = Position(symbol=symbol, qty=qty, avg_price=price)
                s.add(pos)
            else:
                total_qty = pos.qty + qty
                pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total_qty
                pos.qty = total_qty
        else:  # SELL
            if pos is None or pos.qty < qty:
                return OrderResult(False, "insufficient position")
            realized = (price - pos.avg_price) * qty
            cash.cash += price * qty
            pos.qty -= qty
            if pos.qty == 0:
                s.delete(pos)

        trade = Trade(
            symbol=symbol, side=side, qty=qty, price=price,
            strategy=strategy, confidence=confidence, reason=reason, pnl=realized,
        )
        s.add(trade)
        s.flush()

        if side == "SELL" and strategy != "manual":
            update = record_reward(s, strategy, realized)
            s.add(LearningLog(
                kind="insight",
                message=f"Closed {symbol} via {strategy}: pnl={realized:.2f}, "
                        f"running_avg={update['avg_reward']:.2f}",
            ))

        return OrderResult(True, "filled", trade.id, price, realized)


def portfolio_value() -> dict:
    src = get_data_source()
    with get_session() as s:
        cash = _cash_row(s).cash
        positions = s.query(Position).all()
        rows = []
        equity = cash
        for p in positions:
            try:
                last = src.quote(p.symbol).price
            except Exception:
                last = p.avg_price
            mtm = last * p.qty
            unrealized = (last - p.avg_price) * p.qty
            equity += mtm
            rows.append({
                "symbol": p.symbol, "qty": p.qty, "avg_price": p.avg_price,
                "last_price": last, "market_value": mtm, "unrealized_pnl": unrealized,
            })
        return {"cash": cash, "equity": equity, "positions": rows}

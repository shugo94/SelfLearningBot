"""Bar-by-bar backtest engine. Long-only, full position per signal, ATR stops."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from ..strategy.base import Strategy
from ..strategy.ma_crossover import MACrossoverStrategy


@dataclass
class BacktestResult:
    equity_curve: list[dict]
    trades: list[dict]
    metrics: dict


def run(
    df: pd.DataFrame,
    strategy: Strategy | None = None,
    starting_cash: float = 1_000_000.0,
    fee_bps: float = 3.0,  # 0.03% per side ≈ Indian broker + STT-ish
) -> BacktestResult:
    strat = strategy or MACrossoverStrategy()
    cash = starting_cash
    qty = 0
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    trades: list[dict] = []
    equity_curve: list[dict] = []

    # Warmup: first 60 bars feed indicators.
    warmup = 60
    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        bar = window.iloc[-1]
        price = float(bar["Close"])
        ts = bar.name.isoformat() if hasattr(bar.name, "isoformat") else str(bar.name)

        # Exit on stop/target before checking signal.
        if qty > 0 and (
            (stop is not None and price <= stop) or
            (target is not None and price >= target)
        ):
            proceeds = price * qty * (1 - fee_bps / 10000)
            pnl = proceeds - (entry_price * qty * (1 + fee_bps / 10000))
            cash += proceeds
            trades.append({
                "timestamp": ts, "side": "SELL", "price": price, "qty": qty,
                "pnl": pnl, "reason": "stop" if price <= (stop or 0) else "target",
            })
            qty = 0
            entry_price = stop = target = None

        sig = strat.signal(window)
        if sig.action == "BUY" and qty == 0 and sig.confidence > 0.4:
            buy_qty = int(cash // (price * (1 + fee_bps / 10000)))
            if buy_qty > 0:
                cost = buy_qty * price * (1 + fee_bps / 10000)
                cash -= cost
                qty = buy_qty
                entry_price = price
                stop = sig.stop_loss
                target = sig.target
                trades.append({
                    "timestamp": ts, "side": "BUY", "price": price, "qty": qty,
                    "pnl": 0.0, "reason": sig.reason,
                })
        elif sig.action == "SELL" and qty > 0:
            proceeds = price * qty * (1 - fee_bps / 10000)
            pnl = proceeds - (entry_price * qty * (1 + fee_bps / 10000))
            cash += proceeds
            trades.append({
                "timestamp": ts, "side": "SELL", "price": price, "qty": qty,
                "pnl": pnl, "reason": sig.reason,
            })
            qty = 0
            entry_price = stop = target = None

        equity = cash + qty * price
        equity_curve.append({"timestamp": ts, "equity": equity})

    metrics = _summarize(equity_curve, trades, starting_cash)
    return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)


def _summarize(equity_curve: list[dict], trades: list[dict], starting_cash: float) -> dict:
    if not equity_curve:
        return {"final_equity": starting_cash, "return_pct": 0.0, "trades": 0}
    eq = pd.Series([e["equity"] for e in equity_curve])
    rets = eq.pct_change().dropna()
    closed = [t for t in trades if t["side"] == "SELL"]
    wins = [t for t in closed if t["pnl"] > 0]
    win_rate = len(wins) / len(closed) if closed else 0.0
    rolling_max = eq.cummax()
    max_dd = float(((eq - rolling_max) / rolling_max).min()) if len(eq) else 0.0
    sharpe = float(np.sqrt(252) * rets.mean() / rets.std()) if rets.std() else 0.0
    return {
        "final_equity": float(eq.iloc[-1]),
        "return_pct": float((eq.iloc[-1] / starting_cash - 1) * 100),
        "max_drawdown_pct": float(max_dd * 100),
        "sharpe": sharpe,
        "trades": len(closed),
        "win_rate_pct": float(win_rate * 100),
        "avg_pnl_per_trade": float(np.mean([t["pnl"] for t in closed])) if closed else 0.0,
    }

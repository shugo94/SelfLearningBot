"""Rank a universe by a composite score: momentum + trend + breakout + volume.

This is intentionally simple but real. Each component is normalized to [0,1]
and the final score is a weighted sum surfaced as 'AI confidence' in the UI.
"""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from ..config import settings
from ..data import get_data_source
from ..strategy import indicators as ind
from ..strategy.ma_crossover import MACrossoverStrategy


def _score_one(symbol: str) -> dict | None:
    try:
        df = get_data_source().history(symbol, period="6mo", interval="1d")
        if len(df) < 80:
            return None
        feat = ind.add_all(df).dropna()
        last = feat.iloc[-1]

        # Momentum: 1m return + 3m return blended.
        ret_1m = float((last["Close"] / feat["Close"].iloc[-21] - 1) * 100) if len(feat) > 22 else 0
        ret_3m = float((last["Close"] / feat["Close"].iloc[-63] - 1) * 100) if len(feat) > 64 else 0
        momentum_score = _norm(0.5 * ret_1m + 0.5 * ret_3m, -20, 30)

        # Trend: price above SMA50 + SMA20 above SMA50.
        trend = 0.0
        if last["Close"] > last["sma50"]:
            trend += 0.5
        if last["sma20"] > last["sma50"]:
            trend += 0.5

        # Breakout: distance from 20-day high.
        high_20 = feat["High"].rolling(20).max().iloc[-1]
        dist_from_high = (last["Close"] / high_20 - 1) * 100
        breakout_score = 1.0 if dist_from_high >= -0.5 else max(0.0, 1 + dist_from_high / 5)

        # Volume conviction: vol_z bounded.
        vol_score = _norm(float(last["vol_z"]) if pd.notna(last["vol_z"]) else 0, -1, 3)

        composite = (
            0.35 * momentum_score + 0.25 * trend +
            0.25 * breakout_score + 0.15 * vol_score
        )

        sig = MACrossoverStrategy().signal(df)
        return {
            "symbol": symbol,
            "price": float(last["Close"]),
            "ret_1m_pct": round(ret_1m, 2),
            "ret_3m_pct": round(ret_3m, 2),
            "rsi14": round(float(last["rsi14"]), 1),
            "score": round(composite, 3),
            "ai_signal": sig.action,
            "ai_confidence": round(sig.confidence, 3),
            "reason": sig.reason,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def _norm(x: float, lo: float, hi: float) -> float:
    if math.isnan(x):
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def rank(universe: list[str] | None = None, top_n: int = 10) -> list[dict]:
    syms = universe or list(settings.default_universe)
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = [r.result() for r in as_completed([ex.submit(_score_one, s) for s in syms])]
    scored = [r for r in results if r and "score" in r]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_n]

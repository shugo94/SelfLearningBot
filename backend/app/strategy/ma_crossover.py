"""Classic MA-crossover with ATR-derived stop & target. RL-tunable parameters."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import indicators as ind
from .base import Signal, Strategy


@dataclass
class MACrossoverParams:
    fast: int = 20
    slow: int = 50
    rsi_floor: float = 35.0
    rsi_ceiling: float = 75.0
    atr_stop_mult: float = 1.5
    atr_target_mult: float = 3.0


class MACrossoverStrategy(Strategy):
    name = "ma_crossover"

    def __init__(self, params: MACrossoverParams | None = None) -> None:
        self.params = params or MACrossoverParams()

    def signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < self.params.slow + 5:
            return Signal("HOLD", 0.0, "insufficient history")

        feat = ind.add_all(df).dropna()
        if feat.empty:
            return Signal("HOLD", 0.0, "no indicators")

        last = feat.iloc[-1]
        prev = feat.iloc[-2]

        fast_now, slow_now = last["sma20"], last["sma50"]
        fast_prev, slow_prev = prev["sma20"], prev["sma50"]
        price = float(last["Close"])
        atr_val = float(last["atr14"])

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up and self.params.rsi_floor < last["rsi14"] < self.params.rsi_ceiling:
            conf = self._confidence(last, direction="long")
            return Signal(
                "BUY", conf,
                f"SMA{self.params.fast}>SMA{self.params.slow}, RSI={last['rsi14']:.1f}, vol_z={last['vol_z']:.2f}",
                stop_loss=price - self.params.atr_stop_mult * atr_val,
                target=price + self.params.atr_target_mult * atr_val,
            )
        if crossed_down:
            return Signal(
                "SELL", self._confidence(last, direction="short"),
                f"SMA{self.params.fast}<SMA{self.params.slow}, RSI={last['rsi14']:.1f}",
            )
        return Signal("HOLD", 0.2, "no crossover")

    @staticmethod
    def _confidence(last: pd.Series, direction: str) -> float:
        # Bound 0..1. Higher when RSI in mid-range and volume above average.
        rsi_val = float(last["rsi14"])
        vol_z = float(last["vol_z"]) if pd.notna(last["vol_z"]) else 0.0
        rsi_score = 1 - abs(rsi_val - 55) / 55 if direction == "long" else 1 - abs(rsi_val - 45) / 55
        vol_score = min(max(vol_z, 0) / 2, 1)
        return float(min(1.0, max(0.0, 0.5 * rsi_score + 0.5 * vol_score + 0.1)))

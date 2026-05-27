"""Feature engineering for the ML signal — derived from indicators.add_all()."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..strategy import indicators as ind

FEATURE_COLS = [
    "ret_1d", "ret_5d", "ret_10d",
    "rsi14", "macd_hist", "mom10", "vol_z",
    "bb_pos", "sma20_dist", "sma50_dist", "atr_pct",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a feature DataFrame aligned to df.index (NaNs at the head)."""
    feat = ind.add_all(df)
    close = feat["Close"]
    out = pd.DataFrame(index=feat.index)
    out["ret_1d"] = close.pct_change(1)
    out["ret_5d"] = close.pct_change(5)
    out["ret_10d"] = close.pct_change(10)
    out["rsi14"] = feat["rsi14"]
    out["macd_hist"] = feat["macd_hist"]
    out["mom10"] = feat["mom10"]
    out["vol_z"] = feat["vol_z"]
    bb_range = (feat["bb_upper"] - feat["bb_lower"]).replace(0, np.nan)
    out["bb_pos"] = (close - feat["bb_lower"]) / bb_range
    out["sma20_dist"] = (close - feat["sma20"]) / feat["sma20"]
    out["sma50_dist"] = (close - feat["sma50"]) / feat["sma50"]
    out["atr_pct"] = feat["atr14"] / close
    return out


def label_forward_returns(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.01) -> pd.Series:
    """Binary label: 1 if forward `horizon`-bar return > threshold, else 0."""
    fwd = df["Close"].pct_change(horizon).shift(-horizon)
    return (fwd > threshold).astype(int)

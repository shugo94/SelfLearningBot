"""Plain technical indicators. No external TA lib — keeps deps light."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(series, fast) - ema(series, slow)
    sig = ema(macd_line, signal)
    return pd.DataFrame({"macd": macd_line, "signal": sig, "hist": macd_line - sig})


def bollinger(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(series, period)
    std = series.rolling(period, min_periods=period).std()
    return pd.DataFrame({"mid": mid, "upper": mid + num_std * std, "lower": mid - num_std * std})


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_pc = (df["High"] - df["Close"].shift()).abs()
    low_pc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    return series.pct_change(period) * 100


def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with a standard indicator bundle appended."""
    out = df.copy()
    close = out["Close"]
    out["sma20"] = sma(close, 20)
    out["sma50"] = sma(close, 50)
    out["ema20"] = ema(close, 20)
    out["rsi14"] = rsi(close, 14)
    macd_df = macd(close)
    out["macd"] = macd_df["macd"]
    out["macd_signal"] = macd_df["signal"]
    out["macd_hist"] = macd_df["hist"]
    bb = bollinger(close)
    out["bb_upper"] = bb["upper"]
    out["bb_lower"] = bb["lower"]
    out["atr14"] = atr(out, 14)
    out["mom10"] = momentum(close, 10)
    out["vol_z"] = (out["Volume"] - out["Volume"].rolling(20).mean()) / out["Volume"].rolling(20).std()
    return out

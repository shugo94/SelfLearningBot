"""Yahoo Finance adapter via the yfinance lib. 15-min delayed but free + no auth."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
import yfinance as yf

from .base import DataSource, Quote


class YahooDataSource(DataSource):
    name = "yahoo"

    def quote(self, symbol: str) -> Quote:
        df = self._recent(symbol)
        if df.empty:
            raise ValueError(f"no data for {symbol}")
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        change_pct = float((last["Close"] - prev["Close"]) / prev["Close"] * 100) if prev["Close"] else 0.0
        return Quote(
            symbol=symbol,
            price=float(last["Close"]),
            change_pct=change_pct,
            volume=int(last["Volume"]),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        df = yf.download(
            symbol, period=period, interval=interval,
            progress=False, auto_adjust=False, threads=False,
        )
        if df.empty:
            return df
        # yfinance may return MultiIndex cols when symbol is a list; flatten defensively.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        # Yahoo's most recent daily bar often arrives with Close=NaN while the
        # session is still in progress. Don't drop that row — fill Close from
        # the midpoint of today's High/Low so the chart and indicators stay
        # current. Only discard rows that are fully empty.
        missing_close = df["Close"].isna() & df[["Open", "High", "Low"]].notna().all(axis=1)
        df.loc[missing_close, "Close"] = (df.loc[missing_close, "High"] + df.loc[missing_close, "Low"]) / 2
        return df.dropna(subset=["Open", "High", "Low", "Close"])

    @lru_cache(maxsize=128)
    def _recent(self, symbol: str) -> pd.DataFrame:
        return self.history(symbol, period="5d", interval="1d")

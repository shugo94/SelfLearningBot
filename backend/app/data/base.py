"""DataSource interface — all market-data adapters implement this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class Quote:
    symbol: str
    price: float
    change_pct: float
    volume: int
    timestamp: str


class DataSource(ABC):
    name: str = "abstract"

    @abstractmethod
    def quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        """Return OHLCV with columns: Open, High, Low, Close, Volume and a DatetimeIndex."""

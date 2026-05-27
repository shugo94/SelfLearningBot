"""Strategy interface — returns a Signal per bar."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import pandas as pd

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass
class Signal:
    action: Action
    confidence: float  # 0..1
    reason: str
    stop_loss: float | None = None
    target: float | None = None


class Strategy(ABC):
    name: str = "abstract"

    @abstractmethod
    def signal(self, df: pd.DataFrame) -> Signal:
        """Given OHLCV history ending at 'now', return the action for the next bar."""

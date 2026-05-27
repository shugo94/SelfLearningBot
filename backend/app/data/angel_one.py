"""Angel One SmartAPI adapter.

Handles: login + TOTP, instrument-master caching, symbol→token resolution,
LTP quotes, and historical candles. Falls back to Yahoo when not configured
or when a call fails, so the app stays usable.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyotp
import requests
from SmartApi import SmartConnect

from ..config import DATA_DIR
from .base import DataSource, Quote
from .yahoo import YahooDataSource

INSTRUMENT_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
INSTRUMENT_PATH = DATA_DIR / "angel_master.json"
INSTRUMENT_TTL = timedelta(days=7)

# Yahoo-style period → days lookup. Angel requires explicit date ranges.
PERIOD_DAYS = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
    "1y": 365, "2y": 730, "5y": 1825,
}

# Yahoo interval → Angel interval enum + max days per request (Angel limits).
INTERVAL_MAP = {
    "1m":  ("ONE_MINUTE",     30),
    "5m":  ("FIVE_MINUTE",    100),
    "15m": ("FIFTEEN_MINUTE", 200),
    "30m": ("THIRTY_MINUTE",  200),
    "60m": ("ONE_HOUR",       400),
    "1h":  ("ONE_HOUR",       400),
    "1d":  ("ONE_DAY",        2000),
}


@dataclass(frozen=True)
class Instrument:
    exchange: str       # 'NSE' | 'BSE'
    tradingsymbol: str  # e.g. 'RELIANCE-EQ'
    token: str          # e.g. '2885'
    name: str = ""      # e.g. 'RELIANCE INDUSTRIES'


class AngelOneError(RuntimeError):
    pass


class AngelOneDataSource(DataSource):
    name = "angel_one"

    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str) -> None:
        self._api_key = api_key
        self._client_id = client_id
        self._password = password
        self._totp_secret = totp_secret
        self._client: SmartConnect | None = None
        self._lock = threading.Lock()
        self._instruments: dict[str, list[Instrument]] | None = None
        self._instrument_rows: list[Instrument] | None = None
        self._fallback = YahooDataSource()

    # ----- session -----

    def login(self) -> dict:
        """Force a fresh login. Returns the session payload from Angel."""
        with self._lock:
            totp_code = pyotp.TOTP(self._totp_secret).now()
            client = SmartConnect(api_key=self._api_key)
            session = client.generateSession(self._client_id, self._password, totp_code)
            if not session or not session.get("status"):
                raise AngelOneError(f"login failed: {session}")
            self._client = client
            return session

    def _ensure_client(self) -> SmartConnect:
        if self._client is None:
            self.login()
        assert self._client is not None
        return self._client

    # ----- instrument master -----

    def _load_instruments(self) -> dict[str, list[Instrument]]:
        """Download the instrument master (cached for 7d) and index by symbol prefix."""
        if self._instruments is not None:
            return self._instruments

        if (
            not INSTRUMENT_PATH.exists()
            or datetime.now(timezone.utc) - datetime.fromtimestamp(
                INSTRUMENT_PATH.stat().st_mtime, tz=timezone.utc
            ) > INSTRUMENT_TTL
        ):
            resp = requests.get(INSTRUMENT_URL, timeout=60)
            resp.raise_for_status()
            INSTRUMENT_PATH.write_bytes(resp.content)

        raw = json.loads(INSTRUMENT_PATH.read_text())
        index: dict[str, list[Instrument]] = {}
        rows: list[Instrument] = []
        for row in raw:
            if row.get("exch_seg") not in ("NSE", "BSE"):
                continue
            ts = row.get("symbol", "")
            if not ts:
                continue
            name = str(row.get("name") or row.get("symbol") or "")
            inst = Instrument(
                exchange=row["exch_seg"],
                tradingsymbol=ts,
                token=str(row["token"]),
                name=name,
            )
            rows.append(inst)
            # Index by both the bare prefix ("RELIANCE") and the full symbol
            # ("RELIANCE-EQ") so callers can use either.
            base = ts.split("-")[0].upper()
            index.setdefault(base, []).append(inst)
            index.setdefault(ts.upper(), []).append(inst)
        self._instruments = index
        self._instrument_rows = rows
        return index

    def search_symbols(self, query: str, limit: int = 12) -> list[dict]:
        """Return UI-friendly NSE/BSE equity matches for an autocomplete box."""
        q = query.upper().strip()
        if not q:
            return []
        self._load_instruments()
        rows = self._instrument_rows or []

        matches: list[tuple[int, Instrument]] = []
        for inst in rows:
            base = inst.tradingsymbol.split("-")[0].upper()
            name = inst.name.upper()
            is_cash_equity = inst.tradingsymbol.endswith("-EQ") or inst.exchange == "BSE"
            if not is_cash_equity:
                continue
            if base == q:
                score = 0
            elif base.startswith(q):
                score = 1
            elif q in base:
                score = 2
            elif q in name:
                score = 3
            else:
                continue
            exchange_bias = 0 if inst.exchange == "NSE" else 1
            matches.append((score * 10 + exchange_bias, inst))

        matches.sort(key=lambda item: (item[0], item[1].tradingsymbol))
        seen: set[str] = set()
        out: list[dict] = []
        for _, inst in matches:
            base = inst.tradingsymbol.split("-")[0].upper()
            suffix = ".NS" if inst.exchange == "NSE" else ".BO"
            symbol = f"{base}{suffix}"
            if symbol in seen:
                continue
            seen.add(symbol)
            out.append({
                "symbol": symbol,
                "source": "angel_one",
                "exchange": inst.exchange,
                "trading_symbol": inst.tradingsymbol,
                "name": inst.name or base,
                "token": inst.token,
            })
            if len(out) >= limit:
                break
        return out

    def _resolve(self, symbol: str) -> Instrument:
        """Map a Yahoo-style symbol ('RELIANCE.NS') to an Angel instrument."""
        sym = symbol.upper().strip()
        preferred_exchange = "NSE"
        if sym.endswith(".NS"):
            sym = sym[:-3]
        elif sym.endswith(".BO"):
            sym = sym[:-3]
            preferred_exchange = "BSE"

        candidates = self._load_instruments().get(sym, [])
        if not candidates:
            raise AngelOneError(f"unknown symbol on Angel: {symbol}")

        # Prefer exact "<SYM>-EQ" on the preferred exchange (cash equity).
        for c in candidates:
            if c.exchange == preferred_exchange and c.tradingsymbol == f"{sym}-EQ":
                return c
        # Otherwise prefer the right exchange.
        for c in candidates:
            if c.exchange == preferred_exchange:
                return c
        return candidates[0]

    # ----- DataSource interface -----

    def quote(self, symbol: str) -> Quote:
        try:
            inst = self._resolve(symbol)
            client = self._ensure_client()
            with self._lock:
                resp = client.ltpData(inst.exchange, inst.tradingsymbol, inst.token)
            if not resp or not resp.get("status"):
                raise AngelOneError(f"ltpData failed: {resp}")
            d = resp.get("data", {})
            ltp = float(d.get("ltp", 0))
            close = float(d.get("close", ltp))
            change_pct = (ltp - close) / close * 100 if close else 0.0
            return Quote(
                symbol=symbol,
                price=ltp,
                change_pct=change_pct,
                volume=0,  # ltpData doesn't include volume; deeper call needed
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            # Re-login once on auth-ish errors, then fall back to Yahoo.
            if self._looks_like_auth(e):
                try:
                    self.login()
                    return self.quote(symbol)  # one retry
                except Exception:
                    pass
            return self._fallback.quote(symbol)

    def history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        try:
            inst = self._resolve(symbol)
            client = self._ensure_client()
            iv_enum, iv_max_days = INTERVAL_MAP.get(interval, INTERVAL_MAP["1d"])
            days = min(PERIOD_DAYS.get(period, 180), iv_max_days)
            to_dt = datetime.now()
            from_dt = to_dt - timedelta(days=days)
            params = {
                "exchange": inst.exchange,
                "symboltoken": inst.token,
                "interval": iv_enum,
                "fromdate": from_dt.strftime("%Y-%m-%d 09:15"),
                "todate":   to_dt.strftime("%Y-%m-%d 15:30"),
            }
            with self._lock:
                resp = client.getCandleData(params)
            if not resp or not resp.get("status"):
                raise AngelOneError(f"getCandleData failed: {resp}")
            rows = resp.get("data") or []
            if not rows:
                return self._fallback.history(symbol, period, interval)
            df = pd.DataFrame(rows, columns=["t", "Open", "High", "Low", "Close", "Volume"])
            df["t"] = pd.to_datetime(df["t"])
            df = df.set_index("t").sort_index()
            return df[["Open", "High", "Low", "Close", "Volume"]].astype(
                {"Open": float, "High": float, "Low": float, "Close": float, "Volume": "int64"}
            )
        except Exception as e:
            if self._looks_like_auth(e):
                try:
                    self.login()
                    return self.history(symbol, period, interval)
                except Exception:
                    pass
            return self._fallback.history(symbol, period, interval)

    @staticmethod
    def _looks_like_auth(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(k in msg for k in ("token", "session", "unauthorized", "401", "403"))

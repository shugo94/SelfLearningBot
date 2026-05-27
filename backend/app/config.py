"""Central configuration. Override via environment variables or a .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class Settings:
    db_url: str = os.getenv("DB_URL", f"sqlite:///{DATA_DIR / 'selflearningbot.db'}")
    data_source: str = os.getenv("DATA_SOURCE", "yahoo")  # "yahoo" | "angel_one"
    starting_cash: float = float(os.getenv("STARTING_CASH", "1000000"))  # ₹10L paper
    # Default universe for screener + dashboard. Kept small for performance.
    # Symbol search will return all ~10k NSE/BSE stocks if Angel One is configured.
    default_universe: tuple[str, ...] = tuple(
        os.getenv(
            "DEFAULT_UNIVERSE",
            "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS,SBIN.NS,"
            "AXISBANK.NS,LT.NS,ITC.NS,KOTAKBANK.NS,BHARTIARTL.NS,HINDUNILVR.NS,"
            "MARUTI.NS,WIPRO.NS,ONGC.NS,BAJAJFINSV.NS,SUNPHARMA.NS,ASIANPAINT.NS,"
            "BAJAJ-AUTO.NS,JSWSTEEL.NS,TATASTEEL.NS,POWERGRID.NS,GRASIM.NS,UPL.NS",
        ).split(",")
    )
    # Angel One credentials — only needed if data_source == "angel_one"
    angel_api_key: str | None = os.getenv("ANGEL_API_KEY")
    angel_client_id: str | None = os.getenv("ANGEL_CLIENT_ID")
    angel_password: str | None = os.getenv("ANGEL_PASSWORD")
    angel_totp_secret: str | None = os.getenv("ANGEL_TOTP_SECRET")


settings = Settings()

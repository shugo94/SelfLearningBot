"""SQLAlchemy models — trades, positions, strategy parameters, learning log."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY / SELL
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    strategy = Column(String, nullable=False, default="manual")
    confidence = Column(Float, default=0.0)
    reason = Column(Text, default="")
    pnl = Column(Float, default=0.0)  # realized P&L when closing


class Position(Base):
    __tablename__ = "positions"
    symbol = Column(String, primary_key=True)
    qty = Column(Integer, nullable=False, default=0)
    avg_price = Column(Float, nullable=False, default=0.0)
    opened_at = Column(DateTime, default=datetime.utcnow)


class CashAccount(Base):
    __tablename__ = "cash_account"
    id = Column(Integer, primary_key=True)
    cash = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyParam(Base):
    """Persisted, RL-tunable parameters per strategy."""
    __tablename__ = "strategy_params"
    strategy = Column(String, primary_key=True)
    params_json = Column(Text, nullable=False)
    avg_reward = Column(Float, default=0.0)
    n_updates = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LearningLog(Base):
    """Append-only log of what the bot 'learned' — surfaced in UI."""
    __tablename__ = "learning_log"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    kind = Column(String, nullable=False)  # 'insight' | 'request' | 'param_update'
    message = Column(Text, nullable=False)


class BrokerCredentials(Base):
    """Single-row table of broker credentials.

    Stored unencrypted in the local SQLite file. Acceptable for a single-user
    desktop app on a personal machine — but never commit data/*.db and never
    expose this table over a network. Surfaced clearly in the UI.
    """
    __tablename__ = "broker_credentials"
    broker = Column(String, primary_key=True)  # 'angel_one'
    api_key = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    password = Column(String, nullable=False)         # MPIN
    totp_secret = Column(String, nullable=False)      # base32 string, NOT the 6-digit code
    last_login_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

"""Data source factory — dynamic, driven by stored credentials.

Returns the Angel One adapter if credentials are configured in the DB,
otherwise falls back to Yahoo. `reload()` is called by the broker API
whenever credentials are saved/deleted so the swap is immediate.
"""
from __future__ import annotations

import threading

from ..db.models import BrokerCredentials
from ..db.session import get_session
from .base import DataSource
from .angel_one import AngelOneDataSource
from .yahoo import YahooDataSource

_lock = threading.Lock()
_cached: DataSource | None = None
_cached_signature: tuple | None = None


def _current_signature() -> tuple | None:
    with get_session() as s:
        row = s.get(BrokerCredentials, "angel_one")
        if row is None:
            return None
        # Signature includes everything that affects the client identity, so
        # we rebuild only when something actually changes.
        return (row.api_key, row.client_id, row.password, row.totp_secret)


def get_data_source() -> DataSource:
    global _cached, _cached_signature
    sig = _current_signature()
    with _lock:
        if sig != _cached_signature:
            _cached = None
            _cached_signature = sig
        if _cached is None:
            if sig is None:
                _cached = YahooDataSource()
            else:
                api_key, client_id, password, totp = sig
                _cached = AngelOneDataSource(api_key, client_id, password, totp)
        return _cached


def reload() -> DataSource:
    """Force the next get_data_source() call to rebuild."""
    global _cached, _cached_signature
    with _lock:
        _cached = None
        _cached_signature = None
    return get_data_source()

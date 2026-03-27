from __future__ import annotations

import logging
import time
from functools import wraps
from pathlib import Path
from typing import Any

from tigeropen.common.consts import Market, BarPeriod
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient

from config.settings import get_settings

logger = logging.getLogger(__name__)

_instance: TigerClient | None = None


def _retry(max_retries: int = 3, backoff: float = 1.0):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "API call %s failed (attempt %d/%d): %s",
                        fn.__name__, attempt, max_retries, exc,
                    )
                    if attempt < max_retries:
                        time.sleep(backoff * attempt)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


class TigerClient:
    def __init__(self) -> None:
        settings = get_settings()
        # Use props_path — the SDK reads all keys and settings from the .properties file
        config = TigerOpenClientConfig(
            props_path=str(Path(settings.tiger_private_key_path).expanduser())
        )
        self._trade_client = TradeClient(config)
        self._quote_client = QuoteClient(config)
        logger.info("TigerClient initialized for account %s", config.account)

    @_retry()
    def get_option_chain(self, symbol: str, expiry: str) -> list[dict[str, Any]]:
        """Returns list of dicts with keys: identifier, strike, put_call, volume,
        open_interest, pre_close, expiry (timestamp ms), implied_vol, delta."""
        df = self._quote_client.get_option_chain(
            symbol=symbol,
            expiry=expiry,
            market=Market.US,
        )
        if df is None or df.empty:
            return []
        return df.to_dict("records")

    @_retry()
    def get_stock_price(self, symbol: str) -> float:
        """Returns latest stock price; falls back to 0.0 if permission denied."""
        try:
            briefs = self._quote_client.get_stock_briefs([symbol])
            if briefs is None:
                return 0.0
            if hasattr(briefs, 'itertuples'):  # DataFrame
                row = next(briefs.itertuples(), None)
                return float(getattr(row, 'latest_price', 0) or 0)
            elif isinstance(briefs, list) and briefs:
                b = briefs[0]
                return float(getattr(b, 'latest_price', 0) or 0)
        except Exception:
            pass
        return 0.0

    @_retry()
    def get_option_briefs(self, identifiers: list[str]) -> list[dict[str, Any]]:
        """Returns real-time bid/ask/last for specific option contracts."""
        result = self._quote_client.get_option_briefs(identifiers)
        if result is None:
            return []
        if hasattr(result, 'to_dict'):  # DataFrame
            return result.to_dict("records")
        return list(result)

    @_retry()
    def get_option_expirations(self, symbol: str) -> list[str]:
        """Returns list of expiry date strings like ['2026-03-28', ...]."""
        df = self._quote_client.get_option_expirations(symbols=[symbol])
        if df is None or df.empty:
            return []
        return df["date"].tolist()

    @_retry()
    def get_kline(self, symbol: str, period: str = "day", limit: int = 60) -> list[dict[str, Any]]:
        """Returns OHLCV daily bars as list of dicts with keys:
        time (yyyy-MM-dd str), open, high, low, close, volume."""
        bar_period = BarPeriod.DAY if period == "day" else BarPeriod.WEEK
        df = self._quote_client.get_kline(
            symbols=[symbol],
            period=bar_period,
            limit=limit,
            market=Market.US,
        )
        if df is None or df.empty:
            return []
        records = df.to_dict("records")
        result = []
        for row in records:
            # Tiger returns 'time' as ms timestamp; convert to yyyy-MM-dd
            ts = row.get("time") or row.get("timestamp") or row.get("date")
            if ts is None:
                continue
            try:
                from datetime import datetime as _dt
                date_str = _dt.utcfromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
            except Exception:
                date_str = str(ts)
            result.append({
                "time": date_str,
                "open": float(row.get("open", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "volume": int(row.get("volume", 0) or 0),
            })
        return result


def get_tiger_client() -> TigerClient:
    global _instance
    if _instance is None:
        _instance = TigerClient()
    return _instance

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from config.settings import get_settings

from .publisher import FlowPublisher
from .rate_limiter import TokenBucketRateLimiter
from .tiger_client import TigerClient

logger = logging.getLogger(__name__)


@dataclass
class OptionFlow:
    symbol: str
    contract: str
    expiry: str
    strike: float
    right: str  # CALL / PUT
    side: str  # BUY / SELL / MID
    volume_delta: int
    last_price: float
    bid: float
    ask: float
    premium_cents: int
    stock_price: float
    oi: int = 0
    iv: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "contract": self.contract,
            "expiry": self.expiry,
            "strike": str(self.strike),
            "right": self.right,
            "side": self.side,
            "volume_delta": str(self.volume_delta),
            "last_price": str(self.last_price),
            "bid": str(self.bid),
            "ask": str(self.ask),
            "premium_cents": str(self.premium_cents),
            "stock_price": str(self.stock_price),
            "oi": str(self.oi),
            "iv": str(self.iv),
            "timestamp": str(self.timestamp),
        }


def infer_trade_side(last: float, bid: float, ask: float) -> str:
    spread = ask - bid
    if spread <= 0:
        return "MID"
    mid = (bid + ask) / 2
    if last >= ask - spread * 0.3:
        return "BUY"
    elif last <= bid + spread * 0.3:
        return "SELL"
    return "MID"


class OptionChainPoller:
    def __init__(
        self,
        tiger_client: TigerClient,
        rate_limiter: TokenBucketRateLimiter,
        publisher: FlowPublisher,
        on_large_order: Any | None = None,
    ) -> None:
        self._client = tiger_client
        self._limiter = rate_limiter
        self._publisher = publisher
        self._on_large_order = on_large_order
        self._settings = get_settings()
        self._volume_snapshots: dict[str, int] = {}
        self._running = False

    async def start(self, interval: float = 30.0) -> None:
        self._running = True
        logger.info("OptionChainPoller started, interval=%.1fs", interval)
        while self._running:
            cycle_start = time.monotonic()
            try:
                await self._poll_cycle()
            except Exception:
                logger.exception("Error in poll cycle")
            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
        logger.info("OptionChainPoller stopping")

    async def _poll_cycle(self) -> None:
        symbols = self._settings.watchlist_symbols
        threshold = self._settings.premium_threshold_cents

        for symbol in symbols:
            try:
                await self._poll_symbol(symbol, threshold)
            except Exception:
                logger.exception("Error polling %s", symbol)

    async def _poll_symbol(self, symbol: str, threshold: int) -> None:
        await self._limiter.acquire()
        expirations = await asyncio.to_thread(
            self._client.get_option_expirations, symbol
        )
        nearest_expiries = expirations[:4] if len(expirations) >= 4 else expirations

        await self._limiter.acquire()
        stock_info = await asyncio.to_thread(self._client.get_stock_price, symbol)
        stock_price = float(stock_info.get("latestPrice", 0) if isinstance(stock_info, dict) else getattr(stock_info, "latest_price", 0))

        for expiry in nearest_expiries:
            await self._limiter.acquire()
            chain = await asyncio.to_thread(
                self._client.get_option_chain, symbol, expiry
            )
            await self._process_chain(symbol, expiry, chain, stock_price, threshold)

    async def _process_chain(
        self,
        symbol: str,
        expiry: str,
        chain: list[Any],
        stock_price: float,
        threshold: int,
    ) -> None:
        # bid_price / ask_price / latest_price are included in chain response directly
        for item in chain:
            identifier = self._get_field(item, "identifier", "")
            if not identifier:
                continue

            volume = int(self._get_field(item, "volume", 0) or 0)
            prev_volume = self._volume_snapshots.get(identifier, 0)
            self._volume_snapshots[identifier] = volume

            if prev_volume == 0:
                continue

            volume_delta = volume - prev_volume
            if volume_delta <= 0:
                continue

            last_price = float(self._get_field(item, "latest_price", 0) or 0)
            bid = float(self._get_field(item, "bid_price", 0) or 0)
            ask = float(self._get_field(item, "ask_price", 0) or 0)
            pre_close = float(self._get_field(item, "pre_close", 0) or 0)
            price_for_premium = last_price or pre_close
            strike = float(self._get_field(item, "strike", 0) or 0)
            # put_call is full word: 'PUT' or 'CALL'
            right = str(self._get_field(item, "put_call", "") or "").upper()
            oi = int(self._get_field(item, "open_interest", 0) or 0)
            iv = float(self._get_field(item, "implied_volatility", 0) or 0)

            premium_cents = int(volume_delta * price_for_premium * 100 * 100)
            if premium_cents < threshold:
                continue

            side = infer_trade_side(last_price, bid, ask) if last_price > 0 else "MID"

            flow = OptionFlow(
                symbol=symbol,
                contract=identifier,
                expiry=expiry,
                strike=strike,
                right=right,
                side=side,
                volume_delta=volume_delta,
                last_price=price_for_premium,
                bid=bid,
                ask=ask,
                premium_cents=premium_cents,
                stock_price=stock_price,
                oi=oi,
                iv=iv,
            )

            logger.info(
                "Large flow detected: %s %s %.1f %s %s vol=%d premium=$%.0f",
                symbol, expiry, strike, right, side,
                volume_delta, premium_cents / 100,
            )

            await self._publisher.publish(flow.to_dict())

            if self._on_large_order:
                self._on_large_order(identifier)

    @staticmethod
    def _get_field(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

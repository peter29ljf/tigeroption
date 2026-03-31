from __future__ import annotations

import json
import logging
import os
import socket
from collections import deque
from datetime import datetime, timezone

import redis.asyncio as redis

from config.settings import get_settings
from services.processor.accumulation_tracker import AccumulationTracker, accumulation_bonus
from services.processor.ai_interpreter import interpret
from services.processor.db_writer import write_flow
from services.processor.scoring import score_flow
from services.processor.sweep_detector import detect_sweep

logger = logging.getLogger(__name__)

STREAM_RAW = "raw_flows"

# Thresholds for tagging a flow as "abnormal"
_ABNORMAL_SCORE = 75
_ABNORMAL_SWEEP_PREMIUM = 20_000_000   # $200k in cents
_ABNORMAL_DARK_POOL_PREMIUM = 50_000_000  # $500k in cents


def _tag_abnormal(flow: dict) -> None:
    """Set is_abnormal + abnormal_reason on flow in-place."""
    score = int(flow.get("score", 0) or 0)
    premium = int(flow.get("premium", 0) or 0)
    is_sweep = bool(flow.get("is_sweep", False))
    is_dark_pool = bool(flow.get("is_dark_pool", False))

    if score >= _ABNORMAL_SCORE:
        flow["is_abnormal"] = True
        flow["abnormal_reason"] = f"score≥{_ABNORMAL_SCORE}"
    elif is_sweep and premium >= _ABNORMAL_SWEEP_PREMIUM:
        flow["is_abnormal"] = True
        flow["abnormal_reason"] = "大额扫单"
    elif is_dark_pool and premium >= _ABNORMAL_DARK_POOL_PREMIUM:
        flow["is_abnormal"] = True
        flow["abnormal_reason"] = "暗池大单"
    else:
        flow["is_abnormal"] = False
        flow["abnormal_reason"] = None
STREAM_SCORED = "scored_flows"
GROUP_NAME = "processor_group"
BLOCK_MS = 5000
AI_SCORE_THRESHOLD = 70


def _consumer_name() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


_acc_tracker = AccumulationTracker(window_minutes=60)


class FlowConsumer:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._redis: redis.Redis | None = None
        self._sweep_buffer: deque[dict] = deque()
        self._consumer_name = _consumer_name()
        self._running = False

    async def start(self) -> None:
        self._redis = redis.from_url(self._settings.redis_url, decode_responses=True)
        await self._ensure_consumer_group()
        self._running = True
        logger.info(
            "Consumer %s started on group %s", self._consumer_name, GROUP_NAME
        )

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        logger.info("Consumer %s stopped", self._consumer_name)

    async def _ensure_consumer_group(self) -> None:
        assert self._redis is not None
        try:
            await self._redis.xgroup_create(
                STREAM_RAW, GROUP_NAME, id="0", mkstream=True
            )
            logger.info("Created consumer group %s", GROUP_NAME)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def run(self) -> None:
        assert self._redis is not None
        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    GROUP_NAME,
                    self._consumer_name,
                    {STREAM_RAW: ">"},
                    count=100,
                    block=BLOCK_MS,
                )
                if not results:
                    continue

                for _stream_name, messages in results:
                    for msg_id, fields in messages:
                        await self._process_message(msg_id, fields)

            except Exception:
                logger.exception("Error in consumer loop")

    @staticmethod
    def _is_dark_pool(flow: dict) -> bool:
        """Heuristic: large mid-price trade with low vol/OI = likely block/dark-pool-like."""
        premium = int(flow.get("premium", 0))
        side = str(flow.get("side", "")).upper()
        volume = int(flow.get("volume", 0))
        oi = int(flow.get("oi", 0))
        vol_oi = volume / oi if oi > 0 else 0
        return premium >= 50_000_000 and side == "MID" and vol_oi < 0.3

    async def _process_message(self, msg_id: str, fields: dict) -> None:
        assert self._redis is not None
        try:
            flow = self._parse_flow(fields)
            is_sweep = detect_sweep(flow, self._sweep_buffer)
            flow["is_sweep"] = is_sweep
            flow["is_dark_pool"] = self._is_dark_pool(flow)

            flow = score_flow(flow)

            # Accumulation bonus: same symbol+direction 3+ times in 60 min
            direction = str(flow.get("direction", "NEUTRAL"))
            if direction in ("BULLISH", "BEARISH"):
                count = _acc_tracker.record_and_count(
                    str(flow.get("symbol", "")),
                    direction,
                    datetime.now(timezone.utc),
                )
                bonus = accumulation_bonus(count)
                if bonus > 0:
                    flow["score"] = min(int(flow["score"]) + bonus, 100)
                    logger.debug(
                        "Accumulation bonus +%d for %s %s (count=%d)",
                        bonus, flow.get("symbol"), direction, count,
                    )

            if flow["score"] >= AI_SCORE_THRESHOLD:
                ai_note = await interpret(flow)
                flow["ai_note"] = ai_note

            # Mark abnormal flows for the dedicated tab
            _tag_abnormal(flow)

            await write_flow(flow)

            scored_payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                             for k, v in flow.items()
                             if not k.startswith("_")}
            await self._redis.xadd(STREAM_SCORED, scored_payload)

            await self._redis.xack(STREAM_RAW, GROUP_NAME, msg_id)
            logger.debug("Processed message %s: %s score=%s", msg_id, flow.get("symbol"), flow.get("score"))

        except Exception:
            logger.exception("Failed to process message %s", msg_id)

    @staticmethod
    def _parse_flow(fields: dict) -> dict:
        _RENAME = {
            "premium_cents": "premium",
            "volume_delta": "volume",
            "right": "put_call",
            "bid": "bid_price",
            "ask": "ask_price",
            "contract": "raw_identifier",
            "last_price": "last_price",
        }

        flow: dict = {}
        for key, value in fields.items():
            dest = _RENAME.get(key, key)
            if dest in ("premium", "volume", "oi", "dte", "timestamp_ms"):
                try:
                    flow[dest] = int(value)
                except (ValueError, TypeError):
                    flow[dest] = value
            elif dest in ("strike", "bid_price", "ask_price", "stock_price", "iv", "last_price"):
                try:
                    flow[dest] = float(value)
                except (ValueError, TypeError):
                    flow[dest] = value
            elif dest in ("is_sweep", "is_dark_pool"):
                flow[dest] = value in ("True", "true", "1")
            else:
                flow[dest] = value

        if "timestamp" in flow:
            try:
                ts = float(flow["timestamp"])
                flow["timestamp"] = datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, TypeError):
                flow["timestamp"] = datetime.now(timezone.utc)

        if "expiry" in flow and "dte" not in flow:
            try:
                from datetime import date as _date
                exp = _date.fromisoformat(str(flow["expiry"]))
                flow["dte"] = (exp - _date.today()).days
            except (ValueError, TypeError):
                pass

        return flow

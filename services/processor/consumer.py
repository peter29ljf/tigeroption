from __future__ import annotations

import json
import logging
import os
import socket
from collections import deque

import redis.asyncio as redis

from config.settings import get_settings
from services.processor.ai_interpreter import interpret
from services.processor.db_writer import write_flow
from services.processor.scoring import score_flow
from services.processor.sweep_detector import detect_sweep

logger = logging.getLogger(__name__)

STREAM_RAW = "raw_flows"
STREAM_SCORED = "scored_flows"
GROUP_NAME = "processor_group"
BLOCK_MS = 5000
AI_SCORE_THRESHOLD = 70


def _consumer_name() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


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

    async def _process_message(self, msg_id: str, fields: dict) -> None:
        assert self._redis is not None
        try:
            flow = self._parse_flow(fields)
            is_sweep = detect_sweep(flow, self._sweep_buffer)
            flow["is_sweep"] = is_sweep

            flow = score_flow(flow)

            if flow["score"] >= AI_SCORE_THRESHOLD:
                ai_note = await interpret(flow)
                flow["ai_note"] = ai_note

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
        flow: dict = {}
        for key, value in fields.items():
            if key in ("premium", "volume", "oi", "dte", "timestamp_ms"):
                try:
                    flow[key] = int(value)
                except (ValueError, TypeError):
                    flow[key] = value
            elif key in ("strike", "bid_price", "ask_price", "stock_price"):
                try:
                    flow[key] = float(value)
                except (ValueError, TypeError):
                    flow[key] = value
            elif key in ("is_sweep", "is_dark_pool"):
                flow[key] = value in ("True", "true", "1")
            else:
                flow[key] = value
        return flow

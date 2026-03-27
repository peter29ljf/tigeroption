from __future__ import annotations

import logging

import redis.asyncio as aioredis

from config.settings import get_settings

logger = logging.getLogger(__name__)

STREAM_NAME = "raw_flows"
MAXLEN = 50_000


class FlowPublisher:
    def __init__(self) -> None:
        settings = get_settings()
        self._redis: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    async def publish(self, flow_data: dict[str, str]) -> str:
        msg_id = await self._redis.xadd(
            STREAM_NAME, flow_data, maxlen=MAXLEN, approximate=True
        )
        logger.debug("Published flow to %s: %s", STREAM_NAME, msg_id)
        return msg_id

    async def close(self) -> None:
        await self._redis.aclose()
        logger.info("FlowPublisher closed")

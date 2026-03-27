from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ClientSubscription:
    websocket: WebSocket
    symbol: str | None = None
    min_score: int | None = None
    direction: str | None = None


class WebSocketManager:
    def __init__(self) -> None:
        self._clients: dict[WebSocket, ClientSubscription] = {}
        self._redis: aioredis.Redis | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        settings = get_settings()
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._task = asyncio.create_task(self._consume_stream())
        logger.info("WebSocketManager started, consuming scored_flows stream")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
        for client in list(self._clients):
            try:
                await client.close()
            except Exception:
                pass
        self._clients.clear()
        logger.info("WebSocketManager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        symbol: str | None = None,
        min_score: int | None = None,
        direction: str | None = None,
    ) -> None:
        await websocket.accept()
        self._clients[websocket] = ClientSubscription(
            websocket=websocket,
            symbol=symbol,
            min_score=min_score,
            direction=direction,
        )
        logger.info("WebSocket client connected, total=%d", len(self._clients))

    async def disconnect(self, websocket: WebSocket) -> None:
        self._clients.pop(websocket, None)
        logger.info("WebSocket client disconnected, total=%d", len(self._clients))

    def _matches(self, sub: ClientSubscription, flow: dict) -> bool:
        if sub.symbol and flow.get("symbol") != sub.symbol.upper():
            return False
        if sub.min_score is not None:
            score = flow.get("score")
            if score is None or int(score) < sub.min_score:
                return False
        if sub.direction and flow.get("direction") != sub.direction:
            return False
        return True

    async def _broadcast(self, flow: dict) -> None:
        dead: list[WebSocket] = []
        for ws, sub in self._clients.items():
            if not self._matches(sub, flow):
                continue
            try:
                await ws.send_json(flow)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.pop(ws, None)

    async def _consume_stream(self) -> None:
        assert self._redis is not None
        stream_key = "scored_flows"
        last_id = "$"

        try:
            await self._redis.xgroup_create(stream_key, "ws_group", id="$", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        while True:
            try:
                entries = await self._redis.xreadgroup(
                    groupname="ws_group",
                    consumername="ws_consumer",
                    streams={stream_key: ">"},
                    count=50,
                    block=1000,
                )
                if not entries:
                    continue

                for _stream, messages in entries:
                    for msg_id, data in messages:
                        flow_json = data.get("payload") or data.get("data")
                        if flow_json:
                            try:
                                flow = json.loads(flow_json) if isinstance(flow_json, str) else flow_json
                            except (json.JSONDecodeError, TypeError):
                                flow = data
                        else:
                            flow = data
                        await self._broadcast(flow)
                        await self._redis.xack(stream_key, "ws_group", msg_id)

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error consuming Redis stream, retrying in 2s")
                await asyncio.sleep(2)

    async def listen(self, websocket: WebSocket) -> None:
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    data = json.loads(msg)
                    sub = self._clients.get(websocket)
                    if sub:
                        sub.symbol = data.get("symbol", sub.symbol)
                        sub.min_score = data.get("min_score", sub.min_score)
                        sub.direction = data.get("direction", sub.direction)
                except (json.JSONDecodeError, TypeError):
                    pass
        except WebSocketDisconnect:
            await self.disconnect(websocket)

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from tigeropen.push.push_client import PushClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

from config.settings import get_settings

logger = logging.getLogger(__name__)

MONITOR_DURATION = 300  # 5 minutes


class WebSocketSubscriber:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._push_client: PushClient | None = None
        self._subscriptions: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._running = False

    def _init_push_client(self) -> PushClient:
        settings = self._settings
        config = TigerOpenClientConfig(
            props_path=settings.tiger_private_key_path
        )
        protocol, host, port = config.socket_host_port
        client = PushClient(host, port, use_ssl=(protocol == "ssl"))
        client.quote_changed = self._on_quote_changed
        client.connect_callback = self._on_connected
        client.disconnect_callback = self._on_disconnected
        client.error_callback = self._on_error
        return client

    def _get_push_config(self) -> TigerOpenClientConfig:
        return TigerOpenClientConfig(
            props_path=self._settings.tiger_private_key_path
        )

    def _on_connected(self, frame=None) -> None:
        logger.info("WebSocket connected")

    def _on_disconnected(self) -> None:
        logger.warning("WebSocket disconnected")

    def _on_error(self, error: Any) -> None:
        logger.error("WebSocket error: %s", error)

    def _on_quote_changed(self, data: Any) -> None:
        logger.debug("BBO update: %s", data)

    async def start(self) -> None:
        self._running = True
        self._push_client = self._init_push_client()
        config = self._get_push_config()
        self._push_client.connect(config.tiger_id, config.private_key)
        logger.info("WebSocketSubscriber started")
        asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        self._running = False
        if self._push_client:
            try:
                self._push_client.disconnect()
            except Exception:
                logger.exception("Error disconnecting push client")
        logger.info("WebSocketSubscriber stopped")

    def register_contract(self, identifier: str) -> None:
        self._subscriptions[identifier] = time.time()
        if self._push_client:
            try:
                self._push_client.subscribe_option(symbols=[identifier])
                logger.info("Subscribed to BBO for %s", identifier)
            except Exception:
                logger.exception("Failed to subscribe %s", identifier)

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(30)
            now = time.time()
            expired = [
                ident for ident, ts in self._subscriptions.items()
                if now - ts > MONITOR_DURATION
            ]
            for ident in expired:
                self._subscriptions.pop(ident, None)
                if self._push_client:
                    try:
                        self._push_client.unsubscribe_option(symbols=[ident])
                        logger.info("Unsubscribed expired contract %s", ident)
                    except Exception:
                        logger.exception("Failed to unsubscribe %s", ident)

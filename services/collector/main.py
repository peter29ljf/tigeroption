from __future__ import annotations

import asyncio
import logging
import signal

from config.settings import get_settings

from .option_chain_poller import OptionChainPoller
from .publisher import FlowPublisher
from .rate_limiter import TokenBucketRateLimiter
from .tiger_client import get_tiger_client
from .websocket_subscriber import WebSocketSubscriber

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting Collector service")

    publisher = FlowPublisher()
    rate_limiter = TokenBucketRateLimiter(capacity=50, refill_rate=50 / 60)
    tiger_client = get_tiger_client()
    ws_subscriber = WebSocketSubscriber()

    poller = OptionChainPoller(
        tiger_client=tiger_client,
        rate_limiter=rate_limiter,
        publisher=publisher,
        on_large_order=ws_subscriber.register_contract,
    )

    shutdown_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        poller.stop()
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await ws_subscriber.start()

    poller_task = asyncio.create_task(poller.start(interval=30.0))

    await shutdown_event.wait()

    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass

    await ws_subscriber.stop()
    await publisher.close()
    logger.info("Collector service stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

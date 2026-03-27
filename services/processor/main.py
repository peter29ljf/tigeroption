from __future__ import annotations

import asyncio
import logging
import signal

from config.settings import get_settings
from services.processor.consumer import FlowConsumer

logger = logging.getLogger(__name__)


async def _shutdown(consumer: FlowConsumer) -> None:
    logger.info("Shutting down processor...")
    await consumer.stop()


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    consumer = FlowConsumer()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(consumer)))

    await consumer.start()

    try:
        await consumer.run()
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())

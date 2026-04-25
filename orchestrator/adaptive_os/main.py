"""Entry point — starts the orchestrator and API server concurrently."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from adaptive_os.core.config import Config
from adaptive_os.core.orchestrator import Orchestrator
from adaptive_os.api.server import start_server


def setup_logging(config: Config) -> None:
    config.logging.file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.logging.file),
        ],
    )


async def _main() -> None:
    config = Config.load()
    setup_logging(config)

    logger = logging.getLogger("adaptive_os.main")
    logger.info("Starting Adaptive OS v0.1.0")

    orchestrator = Orchestrator(config)

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(orchestrator.stop()))

    await asyncio.gather(
        orchestrator.start(),
        start_server(orchestrator),
    )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()

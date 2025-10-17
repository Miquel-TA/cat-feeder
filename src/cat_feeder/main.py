"""Entry point for cat feeder donation service."""
from __future__ import annotations

import argparse
import asyncio
import logging
import contextlib
import signal
from pathlib import Path

import uvicorn

from .config import AppConfig
from .models import QueueStatus
from .processor import DonationProcessor
from .server import OverlayServer
from .tiktok import TikTokDonationClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main_async(config_path: Path | None = None) -> None:
    config = AppConfig.from_env(config_path)
    if not config.tiktok_username:
        raise RuntimeError("TIKTOK_USERNAME must be configured via environment or config file")

    overlay = OverlayServer(
        config.overlay_static_dir, config.overlay_template_dir, config.status_poll_interval_seconds
    )
    processor = DonationProcessor(config, overlay)
    await processor.start()
    await overlay.send_queue_status(
        QueueStatus(
            active=False,
            sleep_mode=processor.sleep_mode_active,
            seconds_until_wake=processor.time_until_wake().total_seconds(),
        )
    )

    donation_client = TikTokDonationClient(config.tiktok_username, config.reconnect_delay_seconds)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    donation_client.start(processor.enqueue)

    config_uvicorn = uvicorn.Config(overlay.app, host="0.0.0.0", port=8000, loop="asyncio", log_level="info")
    server = uvicorn.Server(config_uvicorn)

    server_task = asyncio.create_task(server.serve())

    await stop_event.wait()

    await donation_client.stop()
    await processor.stop()
    await server.shutdown()
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Cat Feeder donation service")
    parser.add_argument("--config", type=Path, default=None, help="Optional path to JSON configuration file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args.config))


if __name__ == "__main__":
    main()

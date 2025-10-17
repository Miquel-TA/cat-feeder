"""Entry point for the cat feeder service."""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from pathlib import Path

from .arduino import ArduinoController
from .config import AppConfig, load_config
from .display import DisplayServer
from .processor import DonationProcessor
from .queue_manager import DelayedDonationQueue
from .repository import DonationRepository
from .sleep import SleepController
from .sources.base import DonationSource
from .sources.streamlabs import StreamlabsSource

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_sources(config: AppConfig, enqueue) -> list[DonationSource]:
    sources: list[DonationSource] = []
    if config.sources.streamlabs and config.sources.streamlabs.enabled:
        sources.append(StreamlabsSource(config, enqueue))
    return sources


async def run_service(config_path: Path) -> None:
    config = load_config(config_path)
    sleep_controller = SleepController(config.sleep)
    arduino = ArduinoController(config.arduino)
    display = DisplayServer(config, sleep_controller)
    repository = DonationRepository(config.database_path)
    processor = DonationProcessor(display, arduino, repository)
    queue = DelayedDonationQueue(config.queue, processor.process)

    await repository.connect()
    await arduino.start()
    await queue.start()

    async def sleep_callback(sleeping: bool) -> None:
        await arduino.set_sleeping(sleeping)
        await display.broadcast_sleep(sleeping)

    sleep_controller.register_callback(sleep_callback)
    await sleep_callback(sleep_controller.get_state().is_sleeping)

    sources = build_sources(config, queue.enqueue)

    display_task = sleep_task = None
    try:
        for source in sources:
            await source.start()

        display_task = asyncio.create_task(display.run(), name="display-server")
        sleep_task = asyncio.create_task(sleep_controller.run(), name="sleep-controller")

        await asyncio.gather(display_task, sleep_task)
    finally:
        await display.stop()
        if display_task:
            display_task.cancel()
        if sleep_task:
            sleep_task.cancel()
        await asyncio.gather(
            *(task for task in (display_task, sleep_task) if task is not None),
            return_exceptions=True,
        )
        for source in sources:
            try:
                await source.stop()
            except Exception:  # noqa: BLE001
                LOGGER.exception("Failed to stop source %s", source)
        await queue.close()
        await repository.close()
        await arduino.stop()


async def shutdown(loop: asyncio.AbstractEventLoop, tasks: list[asyncio.Task[Any]]) -> None:
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cat Feeder donation orchestrator")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = parser.parse_args()

    configure_logging()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    task = loop.create_task(run_service(args.config), name="cat-feeder-main")

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, task.cancel)

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        LOGGER.info("Shutdown requested")
    finally:
        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for future in pending:
            future.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


if __name__ == "__main__":
    main()

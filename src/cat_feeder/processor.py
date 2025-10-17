"""Core donation processing pipeline."""
from __future__ import annotations

import asyncio
import logging

from .arduino import ArduinoController
from .config import AppConfig, determine_tier
from .models import Donation, QueueStatus
from .queue_manager import DonationQueue
from .server import OverlayServer
from .sleep import SleepScheduler
from .storage import DonationStore

logger = logging.getLogger(__name__)


class DonationProcessor:
    """High level orchestrator bridging TikTok events, overlays, and Arduino."""

    def __init__(self, config: AppConfig, overlay: OverlayServer):
        self._config = config
        self._store = DonationStore(config.database_path)
        self._queue = DonationQueue(config.min_alert_gap_seconds, config.overlay_queue_max)
        self._overlay = overlay
        self._arduino = ArduinoController(config.arduino_port, config.arduino_baud_rate, config.motor_commands)
        self._sleep_scheduler = SleepScheduler.from_strings(
            config.sleep_mode_start, config.sleep_mode_end, config.timezone
        )
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        await self._queue.close()
        if self._task:
            await self._task
        await self._arduino.close()

    async def enqueue(self, username: str, coins: int, comment: str | None) -> None:
        tier_number, tier_def = determine_tier(coins, self._config.tier_thresholds)
        donation = Donation(
            username=username,
            coins=coins,
            tier=tier_number,
            tier_name=tier_def.name,
            message=comment or tier_def.message,
            platform_message=comment,
        )
        await asyncio.to_thread(self._store.add, donation)
        try:
            await self._queue.put(donation)
        except asyncio.CancelledError:
            logger.info("Queue closed, dropping donation event")
            return
        await self._overlay.send_queue_status(
            QueueStatus(
                active=True,
                sleep_mode=self.sleep_mode_active,
                seconds_until_wake=self.time_until_wake().total_seconds(),
            )
        )

    async def _run(self) -> None:
        try:
            async for item in self._queue:
                if self._stop.is_set():
                    break
                donation = item.donation
                sleep_mode = self.sleep_mode_active
                await self._overlay.send_queue_status(
                    QueueStatus(
                        active=True,
                        sleep_mode=sleep_mode,
                        seconds_until_wake=self.time_until_wake().total_seconds(),
                    )
                )
                _, tier_def = determine_tier(donation.coins, self._config.tier_thresholds)
                await self._overlay.send_donation(donation, tier_def.animation, tier_def.sound)
                if not sleep_mode:
                    await self._arduino.trigger_tier(donation.tier)
                else:
                    logger.info("Sleep mode active, skipping Arduino trigger")
                await self._overlay.send_queue_status(
                    QueueStatus(
                        active=False,
                        sleep_mode=sleep_mode,
                        seconds_until_wake=self.time_until_wake().total_seconds(),
                    )
                )
                if self._stop.is_set():
                    break
        except asyncio.CancelledError:
            logger.info("Donation queue closed")

    @property
    def sleep_mode_active(self) -> bool:
        return self._sleep_scheduler.is_sleep_time()

    def time_until_wake(self):
        return self._sleep_scheduler.time_until_wake()


from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Deque, Dict, Iterable, List, Optional

from .arduino import ArduinoController
from .models import Donation, DonationRequest, Settings, Tier
from .sleep import is_sleep_mode_active

LOGGER = logging.getLogger(__name__)


class DonationManager:
    """Coordinates donation intake, alert scheduling, and Arduino triggers."""

    def __init__(self, settings: Settings, arduino: ArduinoController) -> None:
        self.settings = settings
        self.arduino = arduino
        self._queue: "asyncio.Queue[Donation]" = asyncio.Queue()
        self._history: Deque[Donation] = deque(maxlen=1000)
        self._subscribers: List["asyncio.Queue[Dict]"] = []
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        if self._worker_task is None:
            self._shutdown.clear()
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        self.arduino.close()

    async def add_donation(self, request: DonationRequest) -> Donation:
        tier = self._find_tier(request.value)
        donation = Donation(
            username=request.username,
            platform=request.platform,
            value=request.value,
            raw_amount=request.raw_amount,
            message=request.message,
            tier=tier,
        )
        LOGGER.info(
            "Queued donation from %s (%s) with value %.2f",
            donation.username,
            donation.platform,
            donation.value,
        )
        self._history.appendleft(donation)
        await self._queue.put(donation)
        return donation

    def register_subscriber(self) -> "asyncio.Queue[Dict]":
        queue: "asyncio.Queue[Dict]" = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unregister_subscriber(self, queue: "asyncio.Queue[Dict]") -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def recent_donations(self, limit: int = 20) -> List[Donation]:
        return list(self._history)[:limit]

    def _find_tier(self, value: float) -> Optional[Tier]:
        for tier in self.settings.tiers:
            if tier.matches(value):
                return tier
        return None

    async def _worker(self) -> None:
        LOGGER.info("Donation queue worker started")
        delay = max(self.settings.queue_delay_seconds, 0)
        try:
            while not self._shutdown.is_set():
                donation = await self._queue.get()
                await self._dispatch(donation)
                if delay:
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            LOGGER.info("Donation queue worker cancelled")
            raise

    async def _dispatch(self, donation: Donation) -> None:
        payload = donation.to_payload()
        LOGGER.debug("Dispatching donation payload: %s", payload)
        await self._notify_subscribers(payload)
        await self._trigger_arduino(payload)

    async def _notify_subscribers(self, payload: Dict) -> None:
        coros = [queue.put(payload) for queue in list(self._subscribers)]
        if coros:
            results = await asyncio.gather(*coros, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    LOGGER.warning("Subscriber notification failed: %s", result)

    async def _trigger_arduino(self, payload: Dict) -> None:
        motor_id = payload.get("motor")
        if not motor_id:
            return
        if is_sleep_mode_active(self.settings.sleep_mode):
            LOGGER.info("Sleep mode active; skipping motor %s", motor_id)
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.arduino.send_motor_command, motor_id)


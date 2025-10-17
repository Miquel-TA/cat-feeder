"""Donation queue manager with configurable delay."""
from __future__ import annotations

import asyncio
import heapq
import logging
import time
from typing import Awaitable, Callable, List

from .models import DonationEvent, ScheduledDonation
from .config import QueueSettings


LOGGER = logging.getLogger(__name__)


class DelayedDonationQueue:
    """Queue that enforces a minimum gap between donation alerts."""

    def __init__(
        self,
        settings: QueueSettings,
        processor: Callable[[DonationEvent], Awaitable[None]],
    ) -> None:
        self._settings = settings
        self._processor = processor
        self._queue: List[tuple[float, int, ScheduledDonation]] = []
        self._queue_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._counter = 0
        self._next_available_time = time.monotonic()
        self._worker_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker(), name="donation-queue")

    async def close(self) -> None:
        self._closed = True
        self._queue_event.set()
        if self._worker_task is not None:
            await self._worker_task

    async def enqueue(self, donation: DonationEvent) -> None:
        """Schedule a donation for later processing."""
        async with self._lock:
            now = time.monotonic()
            earliest = max(
                self._next_available_time,
                now + self._settings.default_delay_seconds,
            )
            latest = now + self._settings.maximum_delay_seconds
            execute_at = min(earliest, latest)

            scheduled = ScheduledDonation(donation=donation, execute_at=execute_at)
            heapq.heappush(
                self._queue,
                (scheduled.execute_at, self._counter, scheduled),
            )
            self._counter += 1
            LOGGER.info(
                "Queued donation %s for %s at %.2f",
                donation.identifier,
                donation.username,
                execute_at,
            )
            self._queue_event.set()

    async def _worker(self) -> None:
        try:
            while not self._closed:
                await self._queue_event.wait()
                while True:
                    async with self._lock:
                        if not self._queue:
                            self._queue_event.clear()
                            break
                        execute_at, _, scheduled = self._queue[0]
                    now = time.monotonic()
                    delay = execute_at - now
                    if delay > 0:
                        try:
                            await asyncio.wait_for(self._queue_event.wait(), timeout=delay)
                        except asyncio.TimeoutError:
                            pass
                        continue

                    async with self._lock:
                        _, _, scheduled = heapq.heappop(self._queue)
                        if not self._queue:
                            self._queue_event.clear()
                        self._next_available_time = (
                            time.monotonic() + self._settings.minimum_gap_seconds
                        )

                    try:
                        await self._processor(scheduled.donation)
                    except Exception as exc:  # noqa: BLE001
                        scheduled.attempt += 1
                        LOGGER.exception(
                            "Donation processing failed (attempt %s) for %s: %s",
                            scheduled.attempt,
                            scheduled.donation.identifier,
                            exc,
                        )
                        await self._reschedule_on_failure(scheduled)
        except asyncio.CancelledError:  # pragma: no cover - handled gracefully
            LOGGER.info("Donation queue worker cancelled")
        finally:
            LOGGER.info("Donation queue worker stopped")

    async def _reschedule_on_failure(self, scheduled: ScheduledDonation) -> None:
        backoff = min(
            self._settings.minimum_gap_seconds * (scheduled.attempt + 1),
            self._settings.maximum_delay_seconds,
        )
        scheduled.execute_at = time.monotonic() + backoff
        async with self._lock:
            heapq.heappush(self._queue, (scheduled.execute_at, self._counter, scheduled))
            self._counter += 1
            self._queue_event.set()
        LOGGER.info(
            "Re-queued donation %s for retry in %.2f seconds",
            scheduled.donation.identifier,
            backoff,
        )

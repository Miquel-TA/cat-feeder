"""Donation queue handling with throttling support."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Optional

from .models import Donation, QueueItem


class DonationQueue:
    """Queue donations and ensure spacing between alerts."""

    def __init__(self, min_gap_seconds: float, max_items: int):
        self._queue: Deque[QueueItem] = deque()
        self._min_gap = timedelta(seconds=min_gap_seconds)
        self._max_items = max_items
        self._lock = asyncio.Lock()
        self._last_display_time: Optional[datetime] = None
        self._not_empty = asyncio.Condition()
        self._closed = False

    async def put(self, donation: Donation) -> None:
        async with self._lock:
            if self._closed:
                raise asyncio.CancelledError
            if len(self._queue) >= self._max_items:
                # Drop the oldest item to ensure queue keeps flowing.
                self._queue.popleft()
            delay = 0.0
            if self._last_display_time:
                elapsed = datetime.utcnow() - self._last_display_time
                remaining = self._min_gap - elapsed
                delay = max(0.0, remaining.total_seconds())
            self._queue.append(QueueItem(donation=donation, delay_seconds=delay))
            async with self._not_empty:
                self._not_empty.notify()

    async def get(self) -> QueueItem:
        async with self._not_empty:
            while not self._queue:
                if self._closed:
                    raise asyncio.CancelledError
                await self._not_empty.wait()
            item = self._queue.popleft()
        if item.delay_seconds:
            await asyncio.sleep(item.delay_seconds)
        self._last_display_time = datetime.utcnow()
        return item

    async def __aiter__(self):
        while True:
            yield await self.get()

    async def close(self) -> None:
        async with self._not_empty:
            self._closed = True
            self._not_empty.notify_all()

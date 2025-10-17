"""Sleep mode handling."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Awaitable, Callable, List

from zoneinfo import ZoneInfo

from .config import SleepSettings

LOGGER = logging.getLogger(__name__)

StateCallback = Callable[[bool], Awaitable[None]]


@dataclass(slots=True)
class SleepState:
    is_sleeping: bool
    next_transition: datetime


class SleepController:
    def __init__(self, settings: SleepSettings) -> None:
        self._settings = settings
        self._timezone = ZoneInfo(settings.timezone)
        self._callbacks: List[StateCallback] = []
        self._state = SleepState(False, self._compute_next_transition(False))
        self._manual_override: bool | None = None
        self._lock = asyncio.Lock()

    def register_callback(self, callback: StateCallback) -> None:
        self._callbacks.append(callback)

    async def set_manual_override(self, value: bool | None) -> None:
        async with self._lock:
            self._manual_override = value
            state = await self._evaluate_state(force_notify=True)
            if state is not None:
                await self._broadcast(state)

    def get_state(self) -> SleepState:
        return self._state

    async def run(self) -> None:
        while True:
            new_state = await self._evaluate_state()
            if new_state is not None:
                await self._broadcast(new_state)
            await asyncio.sleep(self._settings.check_interval_seconds)

    async def _evaluate_state(self, force_notify: bool = False) -> SleepState | None:
        now = datetime.now(tz=self._timezone)
        is_sleeping = self._is_sleep_period(now)
        if self._manual_override is not None:
            is_sleeping = self._manual_override

        next_transition = self._compute_next_transition(is_sleeping, now)
        new_state = SleepState(is_sleeping, next_transition)

        if force_notify or new_state != self._state:
            LOGGER.info(
                "Sleep state changed: sleeping=%s next_transition=%s",
                new_state.is_sleeping,
                new_state.next_transition,
            )
            self._state = new_state
            return new_state
        return None

    def _is_sleep_period(self, now: datetime) -> bool:
        if not self._settings.enabled:
            return False
        start_dt = datetime.combine(now.date(), self._settings.start, tzinfo=self._timezone)
        end_dt = datetime.combine(now.date(), self._settings.end, tzinfo=self._timezone)

        if self._settings.start < self._settings.end:
            return start_dt <= now < end_dt

        if now >= start_dt:
            return True
        return now < end_dt

    def _compute_next_transition(self, is_sleeping: bool, now: datetime | None = None) -> datetime:
        now = now or datetime.now(tz=self._timezone)
        if not self._settings.enabled:
            return now + timedelta(hours=12)
        start_dt = datetime.combine(now.date(), self._settings.start, tzinfo=self._timezone)
        end_dt = datetime.combine(now.date(), self._settings.end, tzinfo=self._timezone)

        if self._settings.start < self._settings.end:
            return end_dt if is_sleeping else start_dt

        if is_sleeping:
            if now >= start_dt:
                return end_dt + timedelta(days=1)
            return end_dt
        else:
            if now < end_dt:
                return end_dt
            return start_dt + timedelta(days=1)

    async def _broadcast(self, state: SleepState) -> None:
        for callback in list(self._callbacks):
            try:
                await callback(state.is_sleeping)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Sleep callback failed: %s", exc)

"""Base interface for donation sources."""
from __future__ import annotations

import abc
import asyncio
import logging
from typing import Awaitable, Callable

from decimal import Decimal

from ..config import AppConfig, TierMessage
from ..models import DonationEvent

LOGGER = logging.getLogger(__name__)

DonationCallback = Callable[[DonationEvent], Awaitable[None]]


class DonationSource(abc.ABC):
    def __init__(self, config: AppConfig, enqueue: DonationCallback) -> None:
        self._config = config
        self._enqueue = enqueue
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name=self.__class__.__name__)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - not executed in tests
                LOGGER.info("%s stopped", self.__class__.__name__)

    @abc.abstractmethod
    async def _run(self) -> None:
        raise NotImplementedError

    def resolve_tier(self, amount: Decimal) -> TierMessage:
        for tier in sorted(self._config.tiers, key=lambda t: t.minimum_amount, reverse=True):
            if amount >= tier.minimum_amount and (
                tier.maximum_amount is None or amount <= tier.maximum_amount
            ):
                return tier
        return self._config.tiers[0]

    async def emit_donation(
        self,
        username: str,
        platform: str,
        amount: Decimal,
        currency: str,
        message: str,
        raw: dict,
    ) -> None:
        tier = self.resolve_tier(amount)
        rendered_message = tier.message_template.format(
            username=username,
            platform=platform,
            amount=amount,
            currency=currency,
        )
        donation = DonationEvent.from_payload(
            username=username,
            platform=platform,
            amount=amount,
            currency=currency,
            message=rendered_message if rendered_message else message,
            donor_note=message,
            tier=tier,
            raw=raw,
        )
        await self._enqueue(donation)

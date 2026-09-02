"""Donation processing pipeline."""
from __future__ import annotations

import logging

from serial.serialutil import SerialException

from .arduino import ArduinoController
from .display import DisplayServer
from .models import DonationEvent
from .repository import DonationRepository

LOGGER = logging.getLogger(__name__)


class DonationProcessor:
    def __init__(
        self,
        display: DisplayServer,
        arduino: ArduinoController,
        repository: DonationRepository,
    ) -> None:
        self._display = display
        self._arduino = arduino
        self._repository = repository
    async def process(self, donation: DonationEvent) -> None:
        payload = donation.as_display_payload()
        await self._repository.save(payload)
        await self._display.broadcast_donation(payload)
        try:
            await self._arduino.trigger_motor(payload["motor"])
        except SerialException as exc:
            LOGGER.error("Failed to trigger motor: %s", exc)
        LOGGER.info(
            "Processed donation %s from %s (%s %s)",
            donation.identifier,
            donation.username,
            donation.amount,
            donation.currency,
        )

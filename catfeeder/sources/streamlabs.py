"""Streamlabs socket integration for multi-platform donations."""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any, Dict

import socketio

from ..config import AppConfig, StreamlabsSettings
from .base import DonationSource

LOGGER = logging.getLogger(__name__)


class StreamlabsSource(DonationSource):
    """Listen to the Streamlabs socket API for donation events."""

    def __init__(self, config: AppConfig, enqueue) -> None:
        super().__init__(config, enqueue)
        if config.sources.streamlabs is None:
            raise ValueError("Streamlabs configuration missing")
        self._settings: StreamlabsSettings = config.sources.streamlabs
        self._client = socketio.AsyncClient(reconnection=True)
        self._client.on("connect", self._on_connect)
        self._client.on("disconnect", self._on_disconnect)
        self._client.on("event", self._on_event)
        self._stop_event = asyncio.Event()

    async def _run(self) -> None:
        url = f"https://sockets.streamlabs.com?token={self._settings.socket_token}"
        backoff = self._settings.reconnect_backoff_seconds
        while not self._stop_event.is_set():
            try:
                LOGGER.info("Connecting to Streamlabs socket")
                await self._client.connect(
                    url,
                    transports=["websocket"],
                    socketio_path="/socket.io",
                )
                await self._client.wait()
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Streamlabs connection error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._settings.max_backoff_seconds)
            else:
                backoff = self._settings.reconnect_backoff_seconds

    async def stop(self) -> None:
        self._stop_event.set()
        if self._client.connected:
            await self._client.disconnect()
        await super().stop()

    async def _on_connect(self) -> None:
        LOGGER.info("Connected to Streamlabs socket")

    async def _on_disconnect(self) -> None:
        LOGGER.warning("Disconnected from Streamlabs socket")

    async def _on_event(self, data: Dict[str, Any]) -> None:
        message_type = data.get("type")
        for message in data.get("message", []):
            try:
                await self._handle_message(message_type, message)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to handle Streamlabs message: %s", exc)

    async def _handle_message(self, message_type: str, message: Dict[str, Any]) -> None:
        normalized = (message_type or "").lower()
        if normalized in {"donation", "tip"}:
            await self._handle_donation(message)
        elif normalized in {
            "subscription",
            "resub",
            "gift_sub",
            "masssubgift",
            "bits",
            "superchat",
            "superstickers",
            "tiktok_gift",
            "merch",
        }:
            await self._handle_subscription(normalized, message)
        else:
            LOGGER.debug("Unhandled Streamlabs event %s", message_type)

    async def _handle_donation(self, message: Dict[str, Any]) -> None:
        username = message.get("name") or "Anonymous"
        currency = message.get("currency", "EUR")
        amount = Decimal(str(message.get("amount", "0")))
        platform = message.get("platform", "Streamlabs")
        note = message.get("message", "")
        await self.emit_donation(
            username=username,
            platform=platform.capitalize(),
            amount=amount,
            currency=currency,
            message=note,
            raw=message,
        )

    async def _handle_subscription(self, message_type: str, message: Dict[str, Any]) -> None:
        username = (
            message.get("name")
            or message.get("display_name")
            or message.get("user_name")
            or "Anonymous"
        )
        platform = message.get("platform", message.get("channel", "Twitch"))
        amount_value = self._extract_amount(message_type, message)
        amount = Decimal(str(amount_value))
        currency = message.get("currency", message.get("currency_code", "EUR"))
        note = message.get("message", message.get("body", ""))
        await self.emit_donation(
            username=username,
            platform=platform.capitalize(),
            amount=amount,
            currency=currency,
            message=note,
            raw={"type": message_type, **message},
        )

    def _extract_amount(self, message_type: str, message: Dict[str, Any]) -> Decimal:
        if message.get("amount") is not None:
            return Decimal(str(message["amount"]))
        if message_type in {"subscription", "resub"}:
            months = message.get("months") or message.get("streak_months") or 1
            return Decimal(str(months))
        if message_type in {"gift_sub", "masssubgift"}:
            count = message.get("count") or message.get("mass_gift_count") or 1
            return Decimal(str(count))
        if message_type == "bits":
            return Decimal(str(message.get("bits", 0)))
        if message_type == "tiktok_gift":
            return Decimal(str(message.get("repeat_count", 1) * message.get("cost", 1)))
        if message_type in {"superchat", "superstickers"}:
            return Decimal(str(message.get("amount", message.get("displayString", 1))))
        if message_type == "merch":
            return Decimal(str(message.get("total", 1)))
        return Decimal("1")

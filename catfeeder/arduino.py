"""Arduino Nano motor controller integration."""
from __future__ import annotations

import asyncio
import logging
from asyncio import Lock
from typing import Optional

import serial
from serial.serialutil import SerialException

from .config import ArduinoSettings

LOGGER = logging.getLogger(__name__)


class ArduinoController:
    """Wrapper around serial commands to an Arduino Nano."""

    def __init__(self, settings: ArduinoSettings) -> None:
        self._settings = settings
        self._lock = Lock()
        self._serial: Optional[serial.Serial] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._sleeping = False

    async def start(self) -> None:
        await self._ensure_connected()

    async def stop(self) -> None:
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
        if self._serial is not None:
            try:
                self._serial.close()
            except SerialException:
                LOGGER.debug("Serial close failed", exc_info=True)
            self._serial = None

    async def set_sleeping(self, sleeping: bool) -> None:
        LOGGER.info("Arduino sleep state: sleeping=%s", sleeping)
        self._sleeping = sleeping

    async def trigger_motor(self, motor_id: int) -> None:
        if self._sleeping:
            LOGGER.info("Ignoring motor trigger because sleep mode is active")
            return

        await self._write_command(f"MOTOR:{motor_id}\n")

    async def ping(self) -> bool:
        try:
            await self._write_command("PING\n")
            return True
        except SerialException:
            return False

    async def _write_command(self, command: str) -> None:
        await self._ensure_connected()
        async with self._lock:
            if self._serial is None:
                raise SerialException("Serial device is not connected")
            try:
                LOGGER.debug("Sending command to Arduino: %s", command.strip())
                self._serial.write(command.encode("ascii"))
                self._serial.flush()
            except SerialException:
                LOGGER.exception("Failed to write to Arduino. Scheduling reconnect")
                await self._schedule_reconnect()
                raise

    async def _ensure_connected(self) -> None:
        if self._serial is not None and self._serial.is_open:
            return
        try:
            LOGGER.info("Opening serial connection to Arduino on %s", self._settings.port)
            self._serial = serial.Serial(
                self._settings.port,
                self._settings.baudrate,
                timeout=self._settings.command_timeout_seconds,
            )
        except SerialException as exc:
            LOGGER.error("Unable to connect to Arduino: %s", exc)
            await self._schedule_reconnect()
            raise

    async def _schedule_reconnect(self) -> None:
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return

        async def _reconnect() -> None:
            while True:
                try:
                    LOGGER.info("Attempting to reconnect to Arduino")
                    await asyncio.sleep(self._settings.reconnect_interval_seconds)
                    self._serial = serial.Serial(
                        self._settings.port,
                        self._settings.baudrate,
                        timeout=self._settings.command_timeout_seconds,
                    )
                    LOGGER.info("Reconnected to Arduino")
                    break
                except SerialException as exc:  # pragma: no cover - hardware dependent
                    LOGGER.error("Reconnect failed: %s", exc)

        self._reconnect_task = asyncio.create_task(_reconnect(), name="arduino-reconnect")

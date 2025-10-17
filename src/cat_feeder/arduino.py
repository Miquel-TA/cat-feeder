"""Arduino Nano serial communication for triggering motors."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

try:  # pragma: no cover - optional hardware dependency
    import serial
    import serial.tools.list_ports
except ImportError:  # pragma: no cover
    serial = None

logger = logging.getLogger(__name__)


class ArduinoController:
    """Send commands to an Arduino Nano to dispense food."""

    def __init__(self, port: str, baud_rate: int, motor_commands: Dict[int, str]):
        self._port = port
        self._baud_rate = baud_rate
        self._motor_commands = motor_commands
        self._lock = asyncio.Lock()
        self._connection: Optional[serial.Serial] = None

    async def connect(self) -> None:
        if serial is None:
            logger.error("pyserial is not installed; Arduino control disabled")
            return
        async with self._lock:
            if self._connection and self._connection.is_open:
                return
            try:
                self._connection = serial.Serial(self._port, self._baud_rate, timeout=2)
                logger.info("Connected to Arduino on %s", self._port)
            except serial.SerialException:
                logger.exception("Failed to connect to Arduino on %s", self._port)
                self._connection = None

    async def auto_detect_and_connect(self) -> None:
        if serial is None:
            return
        if self._connection and self._connection.is_open:
            return
        for port_info in serial.tools.list_ports.comports():
            if "Arduino" in port_info.description or "USB" in port_info.description:
                self._port = port_info.device
                break
        await self.connect()

    async def trigger_tier(self, tier: int) -> None:
        command = self._motor_commands.get(tier)
        if not command:
            logger.warning("No motor command configured for tier %s", tier)
            return
        if serial is None:
            logger.error("pyserial missing; skipping Arduino trigger")
            return
        async with self._lock:
            if not self._connection or not self._connection.is_open:
                await self.auto_detect_and_connect()
            if not self._connection or not self._connection.is_open:
                logger.error("Unable to trigger motor: Arduino connection unavailable")
                return
            try:
                self._connection.write((command + "\n").encode("utf-8"))
                logger.info("Triggered Arduino motor command %s", command)
            except serial.SerialException:
                logger.exception("Serial communication error; closing connection")
                self._connection.close()
                self._connection = None

    async def close(self) -> None:
        async with self._lock:
            if self._connection and self._connection.is_open:
                self._connection.close()
                self._connection = None

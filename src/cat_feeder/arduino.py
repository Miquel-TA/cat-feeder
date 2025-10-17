from __future__ import annotations

import logging
from contextlib import contextmanager
from threading import Lock
from typing import Optional

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - serial is optional at runtime
    serial = None  # type: ignore

from .models import SerialSettings

LOGGER = logging.getLogger(__name__)


class ArduinoController:
    """Manages serial communication with the Arduino Nano."""

    def __init__(self, settings: SerialSettings) -> None:
        self.settings = settings
        self._lock = Lock()
        self._connection: Optional["serial.Serial"] = None

    def ensure_connected(self) -> None:
        if not self.settings.enabled:
            return
        if serial is None:
            raise RuntimeError(
                "pyserial is required for Arduino communication but is not installed."
            )
        if self._connection and self._connection.is_open:
            return
        LOGGER.info(
            "Opening serial connection to %s at %s baud",
            self.settings.port,
            self.settings.baudrate,
        )
        self._connection = serial.Serial(
            self.settings.port,
            baudrate=self.settings.baudrate,
            timeout=self.settings.timeout,
        )

    def send_motor_command(self, motor_id: int) -> None:
        if not self.settings.enabled:
            LOGGER.debug("Serial disabled; skipping motor %s trigger", motor_id)
            return
        with self._locked_connection() as connection:
            if connection:
                payload = f"MOTOR:{motor_id}\n".encode("utf-8")
                LOGGER.info("Sending command to Arduino: %s", payload)
                connection.write(payload)
                connection.flush()

    @contextmanager
    def _locked_connection(self):
        with self._lock:
            self.ensure_connected()
            yield self._connection

    def close(self) -> None:
        with self._lock:
            if self._connection and self._connection.is_open:
                LOGGER.info("Closing serial connection")
                self._connection.close()
                self._connection = None


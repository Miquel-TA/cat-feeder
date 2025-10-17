from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .models import Settings, Tier, SerialSettings, SleepMode


def load_settings(path: Path) -> Settings:
    raw = _read_json(path)

    tiers = [
        Tier(
            name=item["name"],
            min_value=float(item["min_value"]),
            max_value=float(item["max_value"]) if item.get("max_value") is not None else None,
            message_template=item["message_template"],
            sound=item["sound"],
            animation=item["animation"],
            motor=int(item["motor"]),
        )
        for item in raw.get("tiers", [])
    ]

    serial_settings = SerialSettings(
        enabled=bool(raw.get("serial", {}).get("enabled", False)),
        port=raw.get("serial", {}).get("port", "/dev/ttyUSB0"),
        baudrate=int(raw.get("serial", {}).get("baudrate", 115200)),
        timeout=float(raw.get("serial", {}).get("timeout", 2)),
    )

    sleep_raw = raw.get("sleep_mode", {})
    sleep_mode = SleepMode(
        enabled=bool(sleep_raw.get("enabled", False)),
        start=sleep_raw.get("start", "22:00"),
        end=sleep_raw.get("end", "07:00"),
        timezone=sleep_raw.get("timezone", "UTC"),
    )

    return Settings(
        queue_delay_seconds=float(raw.get("queue_delay_seconds", 8)),
        tiers=tiers,
        serial=serial_settings,
        sleep_mode=sleep_mode,
    )


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


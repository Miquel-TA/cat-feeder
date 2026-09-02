"""Configuration loading for the cat feeder service."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from datetime import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

import yaml


@dataclass(slots=True)
class TierMessage:
    name: str
    minimum_amount: Decimal
    maximum_amount: Optional[Decimal]
    motor: int
    message_template: str
    animation_class: str
    sound: str
    duration_seconds: float = 6.0

    def to_payload(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "motor": self.motor,
            "animation": self.animation_class,
            "sound": self.sound,
            "duration": self.duration_seconds,
        }


@dataclass(slots=True)
class QueueSettings:
    default_delay_seconds: float
    minimum_gap_seconds: float
    maximum_delay_seconds: float


@dataclass(slots=True)
class SleepSettings:
    enabled: bool
    timezone: str
    start: time
    end: time
    check_interval_seconds: int = 30


@dataclass(slots=True)
class ArduinoSettings:
    port: str
    baudrate: int = 9600
    reconnect_interval_seconds: int = 10
    command_timeout_seconds: int = 5


@dataclass(slots=True)
class ServerSettings:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass(slots=True)
class StreamlabsSettings:
    enabled: bool
    socket_token: str
    reconnect_backoff_seconds: int = 5
    max_backoff_seconds: int = 120


@dataclass(slots=True)
class SourceSettings:
    streamlabs: Optional[StreamlabsSettings] = None


@dataclass(slots=True)
class AppConfig:
    queue: QueueSettings
    sleep: SleepSettings
    tiers: List[TierMessage]
    arduino: ArduinoSettings
    server: ServerSettings
    sources: SourceSettings
    database_path: pathlib.Path

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AppConfig":
        queue = QueueSettings(**raw["queue"])
        sleep_cfg = raw["sleep"]
        sleep = SleepSettings(
            enabled=sleep_cfg["enabled"],
            timezone=sleep_cfg["timezone"],
            start=_parse_time(sleep_cfg["start"]),
            end=_parse_time(sleep_cfg["end"]),
            check_interval_seconds=sleep_cfg.get("check_interval_seconds", 30),
        )
        tiers = [
            TierMessage(
                name=entry["name"],
                minimum_amount=Decimal(str(entry["minimum_amount"])),
                maximum_amount=Decimal(str(entry["maximum_amount"]))
                if entry.get("maximum_amount") is not None
                else None,
                motor=entry["motor"],
                message_template=entry["message_template"],
                animation_class=entry["animation_class"],
                sound=entry["sound"],
                duration_seconds=entry.get("duration_seconds", 6.0),
            )
            for entry in raw["tiers"]
        ]
        arduino = ArduinoSettings(**raw["arduino"])
        server = ServerSettings(**raw.get("server", {}))

        source_cfg = raw.get("sources", {})
        streamlabs_cfg = source_cfg.get("streamlabs")
        sources = SourceSettings(
            streamlabs=StreamlabsSettings(**streamlabs_cfg)
            if streamlabs_cfg
            else None
        )

        database_path = pathlib.Path(raw.get("database_path", "data/donations.db"))
        return cls(
            queue=queue,
            sleep=sleep,
            tiers=tiers,
            arduino=arduino,
            server=server,
            sources=sources,
            database_path=database_path,
        )


def load_config(path: pathlib.Path | str) -> AppConfig:
    """Load configuration from YAML file."""
    path = pathlib.Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return AppConfig.from_dict(data)


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))

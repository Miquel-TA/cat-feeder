"""Application configuration and tier definitions for the cat feeder."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import os
import json


DEFAULT_THRESHOLDS = [1, 10, 25, 50, 100]
DEFAULT_MOTOR_COMMANDS = {
    1: "MOTOR1",
    2: "MOTOR2",
    3: "MOTOR3",
    4: "MOTOR4",
    5: "MOTOR5",
}


@dataclass
class TierDefinition:
    """Mapping of minimum coin amount to tier metadata."""

    minimum: int
    name: str
    animation: str
    sound: str
    message: str


@dataclass
class AppConfig:
    """Configuration values for the donation service."""

    tiktok_username: str
    database_path: Path = Path("donations.db")
    min_alert_gap_seconds: float = 8.0
    reconnect_delay_seconds: float = 5.0
    overlay_queue_max: int = 100
    tier_thresholds: List[TierDefinition] = field(default_factory=list)
    motor_commands: Dict[int, str] = field(default_factory=lambda: DEFAULT_MOTOR_COMMANDS.copy())
    arduino_port: str = "COM3"
    arduino_baud_rate: int = 115200
    sleep_mode_start: str = "23:00"  # 24h format
    sleep_mode_end: str = "06:00"
    timezone: str = "UTC"
    status_poll_interval_seconds: int = 10
    overlay_static_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "static")
    overlay_template_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "templates")

    @staticmethod
    def from_env(config_path: Path | None = None) -> "AppConfig":
        """Create configuration from environment variables or optional JSON file."""

        config_data = {}
        if config_path and config_path.exists():
            config_data = json.loads(config_path.read_text())

        def env(key: str, default: str | None = None) -> str | None:
            return os.environ.get(key, config_data.get(key, default))

        thresholds_raw = env("TIER_THRESHOLDS")
        if thresholds_raw:
            thresholds = json.loads(thresholds_raw)
        else:
            thresholds = config_data.get("tier_thresholds") or []
        if not thresholds:
            thresholds = [
                {
                    "minimum": amount,
                    "name": f"Tier {idx + 1}",
                    "animation": f"tier{idx + 1}",
                    "sound": f"tone:tier{idx + 1}",
                    "message": default_tier_message(idx + 1),
                }
                for idx, amount in enumerate(DEFAULT_THRESHOLDS)
            ]

        tier_definitions = [
            TierDefinition(
                minimum=tier["minimum"],
                name=tier.get("name", f"Tier {index + 1}"),
                animation=tier.get("animation", f"tier{index + 1}"),
                sound=tier.get("sound", f"tone:tier{index + 1}"),
                message=tier.get("message", default_tier_message(index + 1)),
            )
            for index, tier in enumerate(thresholds)
        ]

        motor_commands_raw = env("MOTOR_COMMANDS")
        if motor_commands_raw:
            motor_commands = json.loads(motor_commands_raw)
        else:
            motor_commands = config_data.get("motor_commands", DEFAULT_MOTOR_COMMANDS)
        motor_commands = dict(motor_commands)

        default_db = config_data.get("database_path", "donations.db")
        default_static_dir = Path(__file__).resolve().parent / "static"
        default_template_dir = Path(__file__).resolve().parent / "templates"
        static_dir = Path(env("OVERLAY_STATIC_DIR", str(default_static_dir)))
        template_dir = Path(env("OVERLAY_TEMPLATE_DIR", str(default_template_dir)))

        return AppConfig(
            tiktok_username=env("TIKTOK_USERNAME", ""),
            database_path=Path(env("DATABASE_PATH", default_db)),
            min_alert_gap_seconds=float(env("MIN_ALERT_GAP_SECONDS", "8")),
            reconnect_delay_seconds=float(env("RECONNECT_DELAY_SECONDS", "5")),
            overlay_queue_max=int(env("OVERLAY_QUEUE_MAX", "100")),
            tier_thresholds=tier_definitions,
            motor_commands=motor_commands,
            arduino_port=env("ARDUINO_PORT", "COM3"),
            arduino_baud_rate=int(env("ARDUINO_BAUD_RATE", "115200")),
            sleep_mode_start=env("SLEEP_MODE_START", "23:00"),
            sleep_mode_end=env("SLEEP_MODE_END", "06:00"),
            timezone=env("TIMEZONE", "UTC"),
            status_poll_interval_seconds=int(env("STATUS_POLL_INTERVAL_SECONDS", "10")),
            overlay_static_dir=static_dir,
            overlay_template_dir=template_dir,
        )


def default_tier_message(tier: int) -> str:
    """Default celebratory message for a tier."""

    templates = {
        1: "Thanks for your kindness!",
        2: "The cats appreciate your generosity!",
        3: "You unlocked gourmet treats!",
        4: "Feast mode activated!",
        5: "Legendary donor! All cats rejoice!",
    }
    return templates.get(tier, "Thank you for supporting the cats!")


def determine_tier(amount: int, tiers: List[TierDefinition]) -> tuple[int, TierDefinition]:
    """Determine the tier configuration and index for a given donation amount."""

    sorted_tiers = sorted(enumerate(tiers, start=1), key=lambda item: item[1].minimum)
    selected_index, selected = sorted_tiers[0]
    for index, tier in sorted_tiers:
        if amount >= tier.minimum:
            selected_index, selected = index, tier
    return selected_index, selected

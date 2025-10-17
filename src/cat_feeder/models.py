from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


@dataclass
class Tier:
    name: str
    min_value: float
    max_value: Optional[float]
    message_template: str
    sound: str
    animation: str
    motor: int

    def matches(self, value: float) -> bool:
        if value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True


@dataclass
class SleepMode:
    enabled: bool
    start: str  # HH:MM 24h format
    end: str  # HH:MM 24h format
    timezone: str


@dataclass
class SerialSettings:
    enabled: bool
    port: str
    baudrate: int
    timeout: float = 2.0


@dataclass
class Settings:
    queue_delay_seconds: float
    tiers: List[Tier]
    serial: SerialSettings
    sleep_mode: SleepMode


@dataclass
class Donation:
    username: str
    platform: str
    value: float
    raw_amount: str
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tier: Optional[Tier] = None

    def to_payload(self) -> dict:
        return {
            "username": self.username,
            "platform": self.platform,
            "value": self.value,
            "raw_amount": self.raw_amount,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "tier": self.tier.name if self.tier else None,
            "display_message": self.tier.message_template.format(
                username=self.username,
                platform=self.platform,
                message=self.message,
                raw_amount=self.raw_amount,
                value=self.value,
            )
            if self.tier
            else self.message,
            "sound": self.tier.sound if self.tier else None,
            "animation": self.tier.animation if self.tier else None,
            "motor": self.tier.motor if self.tier else None,
        }


class DonationRequest(BaseModel):
    username: str
    platform: str
    raw_amount: str
    value: float
    message: str = ""



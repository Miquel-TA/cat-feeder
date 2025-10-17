"""Data models used across the cat feeder application."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Donation:
    """Represents a single donation/subscription event."""

    username: str
    coins: int
    tier: int
    tier_name: str
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    platform_message: Optional[str] = None
    profile_picture: Optional[str] = None


@dataclass
class QueueItem:
    """Donation item queued for alert display."""

    donation: Donation
    delay_seconds: float


@dataclass
class QueueStatus:
    """State reported to overlay clients."""

    active: bool
    sleep_mode: bool
    seconds_until_wake: float

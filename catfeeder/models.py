"""Dataclasses representing domain objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from .config import TierMessage


@dataclass(slots=True)
class DonationEvent:
    identifier: str
    username: str
    platform: str
    amount: Decimal
    currency: str
    message: str
    donor_note: str = ""
    tier: TierMessage
    raw: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())

    @classmethod
    def from_payload(
        cls,
        username: str,
        platform: str,
        amount: Decimal,
        currency: str,
        message: str,
        tier: TierMessage,
        donor_note: str = "",
        raw: Optional[Dict[str, Any]] = None,
    ) -> "DonationEvent":
        return cls(
            identifier=str(uuid.uuid4()),
            username=username,
            platform=platform,
            amount=amount,
            currency=currency,
            message=message,
            donor_note=donor_note,
            tier=tier,
            raw=raw or {},
        )

    def as_display_payload(self) -> Dict[str, Any]:
        payload = {
            "id": self.identifier,
            "username": self.username,
            "platform": self.platform,
            "amount": str(self.amount),
            "currency": self.currency,
            "message": self.message,
            "donor_note": self.donor_note,
            "created_at": self.created_at.isoformat(),
        }
        payload.update(self.tier.to_payload())
        return payload


@dataclass(slots=True)
class ScheduledDonation:
    donation: DonationEvent
    execute_at: float
    attempt: int = 0

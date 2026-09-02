"""Sleep mode scheduling helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass
class SleepScheduler:
    """Determines whether the system should operate or stay in sleep mode."""

    start: time
    end: time
    timezone: ZoneInfo
    manual_override: bool = False

    @classmethod
    def from_strings(cls, start: str, end: str, timezone: str) -> "SleepScheduler":
        tz = ZoneInfo(timezone)
        return cls(
            start=_parse_time(start),
            end=_parse_time(end),
            timezone=tz,
        )

    def is_sleep_time(self, moment: datetime | None = None) -> bool:
        if self.manual_override:
            return True
        moment = moment or datetime.now(self.timezone)
        now_time = moment.timetz()
        if self.start < self.end:
            return self.start <= now_time < self.end
        # Over midnight window
        return now_time >= self.start or now_time < self.end

    def time_until_wake(self, moment: datetime | None = None) -> timedelta:
        moment = moment or datetime.now(self.timezone)
        now_time = moment.timetz()
        if not self.is_sleep_time(moment):
            return timedelta(0)
        today = moment.date()
        end_datetime = datetime.combine(today, self.end, tzinfo=self.timezone)
        if self.start > self.end:
            # Next day end
            if now_time < self.end:
                end_datetime = datetime.combine(today, self.end, tzinfo=self.timezone)
            else:
                end_datetime = datetime.combine(today + timedelta(days=1), self.end, tzinfo=self.timezone)
        elif now_time >= self.end:
            end_datetime = datetime.combine(today + timedelta(days=1), self.end, tzinfo=self.timezone)
        return max(timedelta(0), end_datetime - moment)


def _parse_time(value: str) -> time:
    hour, minute = map(int, value.split(":"))
    return time(hour=hour, minute=minute)
